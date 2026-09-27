//! Trino profile validation and ADBC connection options.
//!
//! Profiles follow the dbt-trino v1 credential fields:
//! <https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/adapters/trino/connections.py>
//!
//! The ADBC Trino driver (<https://github.com/adbc-drivers/trino>) hands its URI to
//! trino-go-client, so every option below maps to a DSN query parameter documented in
//! <https://github.com/trinodb/trino-go-client/blob/v0.336.0/trino/trino.go>.

use crate::{AdapterConfig, Auth, AuthError, AuthWarningPrinter};
use dbt_adbc::{Backend, database};
use dbt_yaml::Value as YmlValue;
use url::Url;

pub const BACKEND: Backend = Backend::Generic {
    library_name: "adbc_driver_trino",
    entrypoint: None,
};

/// dbt-trino v1 sends `X-Trino-Source: dbt-trino-<version>`. Trino resource-group selectors
/// commonly match on it, so the prefix is kept.
const SOURCE_PREFIX: &str = "dbt-trino-";

/// Methods accepted by dbt-trino v1 that the ADBC Trino driver cannot perform.
const UNSUPPORTED_METHODS: [(&str, &str); 4] = [
    (
        "certificate",
        "client certificate (mTLS) authentication is not supported by the ADBC Trino driver",
    ),
    (
        "gssapi",
        "GSSAPI ticket-cache authentication is not supported by the ADBC Trino driver; \
         use method: kerberos with a keytab",
    ),
    (
        "oauth",
        "interactive OAuth2 is not supported by the ADBC Trino driver; \
         obtain a token and use method: jwt",
    ),
    (
        "oauth_console",
        "interactive OAuth2 is not supported by the ADBC Trino driver; \
         obtain a token and use method: jwt",
    ),
];

pub struct TrinoAuth {
    warning_printer: Box<dyn AuthWarningPrinter>,
}

impl TrinoAuth {
    pub fn new(warning_printer: Box<dyn AuthWarningPrinter>) -> Self {
        Self { warning_printer }
    }
}

impl Auth for TrinoAuth {
    fn backend(&self) -> Backend {
        BACKEND
    }

    fn configure(&self, config: &AdapterConfig) -> Result<database::Builder, AuthError> {
        let host = required(config, "host")?;
        let catalog = required(config, "database")?;
        let schema = required(config, "schema")?;
        let port = config
            .get_string("port")
            .and_then(|value| value.parse::<u16>().ok())
            .filter(|port| *port != 0)
            .ok_or_else(|| AuthError::config("Trino requires a port between 1 and 65535"))?;

        for key in [
            "method",
            "http_scheme",
            "user",
            "password",
            "jwt_token",
            "timezone",
            "keytab",
            "principal",
            "krb5_config",
            "service_name",
            "query_timeout",
        ] {
            if config.get(key).is_some_and(|value| !value.is_null())
                && config.get_str(key).is_none()
            {
                return Err(AuthError::config(format!("Trino '{key}' must be a string")));
            }
        }
        for key in ["impersonation_user", "http_headers", "role"] {
            if config.get(key).is_some_and(|value| !value.is_null()) {
                return Err(AuthError::config(format!(
                    "Trino '{key}' is not supported by the ADBC Trino driver"
                )));
            }
        }

        let method = config.get_str("method").unwrap_or("none");
        if let Some((_, reason)) = UNSUPPORTED_METHODS.iter().find(|(m, _)| *m == method) {
            return Err(AuthError::config(format!(
                "Trino method {method}: {reason}"
            )));
        }
        // dbt-trino v1 forces HTTPS for authenticated methods and defaults to HTTP otherwise.
        let scheme = match (method, config.get_str("http_scheme")) {
            ("none", None) => "http",
            ("none", Some(scheme @ ("http" | "https"))) => scheme,
            ("none", Some(_)) => {
                return Err(AuthError::config(
                    "Trino 'http_scheme' must be http or https",
                ));
            }
            ("ldap" | "jwt" | "kerberos", None | Some("https")) => "https",
            ("ldap" | "jwt" | "kerberos", Some(_)) => {
                return Err(AuthError::config(format!(
                    "Trino method {method} requires http_scheme: https"
                )));
            }
            _ => {
                return Err(AuthError::config(format!(
                    "Unknown Trino method '{method}'; supported methods are none, ldap, jwt \
                     and kerberos"
                )));
            }
        };

        let mut uri = Url::parse("https://localhost").expect("valid constant URI");
        uri.set_scheme(scheme)
            .map_err(|_| AuthError::config("Invalid Trino HTTP scheme"))?;
        uri.set_host(Some(host))
            .map_err(|_| AuthError::config("Invalid Trino host"))?;
        uri.set_port(Some(port))
            .map_err(|_| AuthError::config("Invalid Trino port"))?;

        let mut builder = database::Builder::new(BACKEND);
        let mut query = Vec::<(&str, String)>::new();
        let user = non_empty(config, "user");
        match method {
            "none" => {
                if non_empty(config, "password").is_some() {
                    return Err(AuthError::config("A Trino password requires method ldap"));
                }
                builder.with_username(user.ok_or_else(|| missing("user"))?);
            }
            "ldap" => {
                builder.with_username(user.ok_or_else(|| missing("user"))?);
                builder.with_password(
                    non_empty(config, "password").ok_or_else(|| {
                        AuthError::config("Trino method ldap requires a password")
                    })?,
                );
            }
            "jwt" => {
                if let Some(user) = user {
                    builder.with_username(user);
                }
                let token = non_empty(config, "jwt_token")
                    .ok_or_else(|| AuthError::config("Trino method jwt requires jwt_token"))?;
                query.push(("accessToken", token.to_string()));
            }
            "kerberos" => {
                builder.with_username(user.ok_or_else(|| missing("user"))?);
                query.extend(kerberos_options(config)?);
            }
            _ => unreachable!("method validated above"),
        }

        query.push(("catalog", catalog.to_string()));
        query.push(("schema", schema.to_string()));
        query.push((
            "source",
            format!("{SOURCE_PREFIX}{}", env!("CARGO_PKG_VERSION")),
        ));
        if let Some(roles) = string_map(config, "roles")? {
            query.push(("roles", roles));
        }
        if let Some(properties) = string_map(config, "session_properties")? {
            query.push(("session_properties", properties));
        }
        if let Some(tags) = client_tags(config)? {
            query.push(("clientTags", tags));
        }
        if let Some(timezone) = non_empty(config, "timezone") {
            query.push(("timezone", timezone.to_string()));
        }
        if let Some(timeout) = non_empty(config, "query_timeout") {
            query.push(("query_timeout", timeout.to_string()));
        }
        if let Some(enabled) = bool_field(config, "prepared_statements_enabled")? {
            query.push(("explicitPrepare", enabled.to_string()));
        }
        match (scheme, config.get("cert")) {
            (_, None | Some(YmlValue::Null(..))) | ("https", Some(YmlValue::Bool(true, ..))) => {}
            ("https", Some(YmlValue::Bool(false, ..))) => {
                // dbt-trino v1 also warns unless `suppress_cert_warning` is set.
                if bool_field(config, "suppress_cert_warning")? != Some(true) {
                    self.warning_printer.warn(
                        "Trino TLS certificate verification is disabled (cert: false); set \
                         `cert` to a CA bundle path instead",
                    );
                }
                query.push(("SSLVerification", "NONE".to_string()));
            }
            ("https", Some(YmlValue::String(path, ..))) if !path.is_empty() => {
                query.push(("SSLCertPath", path.clone()));
            }
            ("http", Some(_)) => {
                return Err(AuthError::config(
                    "Trino 'cert' requires http_scheme: https",
                ));
            }
            _ => {
                return Err(AuthError::config(
                    "Trino 'cert' must be true, false or a CA bundle path",
                ));
            }
        }
        if config.get("retries").is_some_and(|value| !value.is_null()) {
            // Accepted for dbt-trino v1 profile compatibility.
            self.warning_printer.warn(
                "Trino 'retries' is ignored: the ADBC Trino driver has no client-side retry setting",
            );
        }

        {
            let mut pairs = uri.query_pairs_mut();
            for (key, value) in &query {
                pairs.append_pair(key, value);
            }
        }
        builder.with_uri(uri);
        Ok(builder)
    }
}

fn missing(key: &str) -> AuthError {
    AuthError::config(format!("Trino requires '{key}' in the profile"))
}

fn non_empty<'a>(config: &'a AdapterConfig, key: &str) -> Option<&'a str> {
    config.get_str(key).filter(|value| !value.is_empty())
}

fn required<'a>(config: &'a AdapterConfig, key: &str) -> Result<&'a str, AuthError> {
    non_empty(config, key).ok_or_else(|| missing(key))
}

fn bool_field(config: &AdapterConfig, key: &str) -> Result<Option<bool>, AuthError> {
    match config.get(key) {
        None | Some(YmlValue::Null(..)) => Ok(None),
        Some(YmlValue::Bool(value, ..)) => Ok(Some(*value)),
        Some(YmlValue::String(value, ..)) if value.eq_ignore_ascii_case("true") => Ok(Some(true)),
        Some(YmlValue::String(value, ..)) if value.eq_ignore_ascii_case("false") => Ok(Some(false)),
        Some(_) => Err(AuthError::config(format!(
            "Trino '{key}' must be a boolean"
        ))),
    }
}

fn scalar(value: &YmlValue) -> Option<String> {
    match value {
        YmlValue::String(s, ..) => Some(s.clone()),
        YmlValue::Bool(b, ..) => Some(b.to_string()),
        YmlValue::Number(n, ..) => Some(n.to_string()),
        _ => None,
    }
}

/// Render a profile mapping in trino-go-client's `key:value;key:value` DSN syntax.
fn string_map(config: &AdapterConfig, key: &str) -> Result<Option<String>, AuthError> {
    let mapping = match config.get(key) {
        None | Some(YmlValue::Null(..)) => return Ok(None),
        Some(YmlValue::Mapping(mapping, ..)) => mapping,
        Some(_) => {
            return Err(AuthError::config(format!(
                "Trino '{key}' must be a mapping"
            )));
        }
    };
    let mut entries = Vec::with_capacity(mapping.len());
    for (name, value) in mapping {
        let (Some(name), Some(value)) = (scalar(name), scalar(value)) else {
            return Err(AuthError::config(format!(
                "Trino '{key}' must map strings to scalar values"
            )));
        };
        if name.is_empty() || name.contains([':', ';']) || value.contains(';') {
            return Err(AuthError::config(format!(
                "Trino '{key}' entries cannot contain ';', and keys cannot contain ':'"
            )));
        }
        entries.push(format!("{name}:{value}"));
    }
    entries.sort();
    Ok((!entries.is_empty()).then(|| entries.join(";")))
}

fn client_tags(config: &AdapterConfig) -> Result<Option<String>, AuthError> {
    let tags = match config.get("client_tags") {
        None | Some(YmlValue::Null(..)) => return Ok(None),
        Some(YmlValue::Sequence(tags, ..)) => tags,
        Some(_) => return Err(AuthError::config("Trino 'client_tags' must be a list")),
    };
    let mut out = Vec::with_capacity(tags.len());
    for tag in tags {
        match tag {
            YmlValue::String(tag, ..) if !tag.contains(',') => out.push(tag.as_str()),
            _ => {
                return Err(AuthError::config(
                    "Trino 'client_tags' entries must be strings without commas",
                ));
            }
        }
    }
    Ok((!out.is_empty()).then(|| out.join(",")))
}

fn kerberos_options(config: &AdapterConfig) -> Result<Vec<(&'static str, String)>, AuthError> {
    let keytab = non_empty(config, "keytab").ok_or_else(|| {
        AuthError::config(
            "Trino method kerberos requires 'keytab'; ticket-cache authentication is not \
             supported by the ADBC Trino driver",
        )
    })?;
    let principal = non_empty(config, "principal").ok_or_else(|| missing("principal"))?;
    let (principal, realm) = principal.rsplit_once('@').ok_or_else(|| {
        AuthError::config("Trino Kerberos 'principal' must include a realm, e.g. dbt@EXAMPLE.COM")
    })?;
    for key in [
        "hostname_override",
        "force_preemptive",
        "delegate",
        "mutual_authentication",
    ] {
        let enabled = match config.get(key) {
            None | Some(YmlValue::Null(..) | YmlValue::Bool(false, ..)) => false,
            Some(YmlValue::String(value, ..)) => !value.eq_ignore_ascii_case("disabled"),
            Some(_) => true,
        };
        if enabled {
            return Err(AuthError::config(format!(
                "Trino Kerberos option '{key}' is not supported by the ADBC Trino driver"
            )));
        }
    }
    // dbt-trino v1 reads the krb5 configuration from KRB5_CONFIG.
    let krb5_config = non_empty(config, "krb5_config")
        .map(str::to_string)
        .or_else(|| std::env::var("KRB5_CONFIG").ok())
        .unwrap_or_else(|| "/etc/krb5.conf".to_string());
    let mut options = vec![
        ("KerberosEnabled", "true".to_string()),
        ("KerberosKeytabPath", keytab.to_string()),
        ("KerberosPrincipal", principal.to_string()),
        ("KerberosRealm", realm.to_string()),
        ("KerberosConfigPath", krb5_config),
    ];
    if let Some(service) = non_empty(config, "service_name") {
        options.push(("KerberosRemoteServiceName", service.to_string()));
    }
    Ok(options)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_options::uri_value;
    use dbt_yaml::Mapping;
    use std::collections::HashMap;
    use std::sync::{Arc, Mutex};

    fn profile() -> Mapping {
        Mapping::from_iter([
            ("host".into(), "trino.example.test".into()),
            ("port".into(), 8443.into()),
            ("user".into(), "test_user".into()),
            ("database".into(), "iceberg".into()),
            ("schema".into(), "analytics".into()),
        ])
    }

    #[derive(Clone, Default)]
    struct RecordedWarnings(Arc<Mutex<Vec<String>>>);

    impl AuthWarningPrinter for RecordedWarnings {
        fn warn(&self, message: &str) {
            self.0.lock().unwrap().push(message.to_string());
        }
    }

    fn configure_with_warnings(
        pairs: &[(&str, YmlValue)],
    ) -> (Result<database::Builder, AuthError>, Vec<String>) {
        let mut config = profile();
        for (key, value) in pairs {
            config.insert((*key).into(), value.clone());
        }
        let warnings = RecordedWarnings::default();
        let result =
            TrinoAuth::new(Box::new(warnings.clone())).configure(&AdapterConfig::new(config));
        let recorded = warnings.0.lock().unwrap().clone();
        (result, recorded)
    }

    fn configure(pairs: &[(&str, YmlValue)]) -> Result<database::Builder, AuthError> {
        configure_with_warnings(pairs).0
    }

    fn yaml(text: &str) -> YmlValue {
        dbt_yaml::from_str(text).unwrap()
    }

    fn query(builder: &database::Builder) -> HashMap<String, String> {
        Url::parse(&uri_value(builder))
            .unwrap()
            .query_pairs()
            .into_owned()
            .collect()
    }

    #[test]
    fn method_none_defaults_to_http_like_dbt_trino_v1() {
        for port in [YmlValue::from(8080), "8080".into()] {
            let builder = configure(&[("port", port)]).unwrap();
            let uri = Url::parse(&uri_value(&builder)).unwrap();
            assert_eq!(uri.scheme(), "http");
            assert_eq!(uri.port(), Some(8080));
            assert_eq!(builder.username.as_deref(), Some("test_user"));
            let query = query(&builder);
            assert_eq!(query["catalog"], "iceberg");
            assert_eq!(query["schema"], "analytics");
            assert!(query["source"].starts_with("dbt-trino-"));
        }
    }

    #[test]
    fn ldap_uses_https_and_keeps_password_out_of_uri() {
        let builder = configure(&[
            ("method", "ldap".into()),
            ("password", "p@ss:word&SSL=false".into()),
        ])
        .unwrap();
        let uri = uri_value(&builder);
        assert!(uri.starts_with("https://trino.example.test:8443"));
        assert!(!uri.contains("p@ss") && !uri.contains("p%40ss"));
        assert_eq!(builder.password.as_deref(), Some("p@ss:word&SSL=false"));
    }

    #[test]
    fn authenticated_methods_reject_http() {
        for (method, extra) in [
            ("ldap", ("password", YmlValue::from("secret"))),
            ("jwt", ("jwt_token", YmlValue::from("secret"))),
        ] {
            let err = configure(&[
                ("method", method.into()),
                ("http_scheme", "http".into()),
                extra,
            ])
            .unwrap_err();
            assert!(
                err.msg().contains("requires http_scheme: https"),
                "{method}"
            );
            assert!(!format!("{err:?}").contains("secret"));
        }
    }

    #[test]
    fn jwt_sends_access_token_and_optional_user() {
        let builder = configure(&[
            ("method", "jwt".into()),
            ("jwt_token", "abc.def.ghi".into()),
        ])
        .unwrap();
        assert_eq!(query(&builder)["accessToken"], "abc.def.ghi");
        assert!(configure(&[("method", "jwt".into())]).is_err());
    }

    #[test]
    fn session_options_map_to_dsn_parameters() {
        let builder = configure(&[
            ("roles", yaml("{hive: admin, system: ALL}")),
            (
                "session_properties",
                yaml(
                    "{query_max_run_time: 5m, hive.insert_existing_partitions_behavior: OVERWRITE, \
                     retry_count: 2}",
                ),
            ),
            ("client_tags", yaml("[etl, nightly]")),
            ("timezone", "UTC".into()),
            ("prepared_statements_enabled", false.into()),
            ("query_timeout", "30m".into()),
            ("retries", 3.into()),
        ])
        .unwrap();
        let query = query(&builder);
        assert_eq!(query["roles"], "hive:admin;system:ALL");
        assert_eq!(
            query["session_properties"],
            "hive.insert_existing_partitions_behavior:OVERWRITE;query_max_run_time:5m;\
             retry_count:2"
        );
        assert_eq!(query["clientTags"], "etl,nightly");
        assert_eq!(query["timezone"], "UTC");
        assert_eq!(query["explicitPrepare"], "false");
        assert_eq!(query["query_timeout"], "30m");
    }

    #[test]
    fn map_values_cannot_inject_extra_entries() {
        assert!(configure(&[("session_properties", yaml("{a: 'x;b:y'}"))]).is_err());
        assert!(configure(&[("roles", yaml("{'a:b': admin}"))]).is_err());
        assert!(configure(&[("client_tags", yaml("['a,b']"))]).is_err());
    }

    #[test]
    fn cert_controls_tls_verification() {
        let https = |cert: YmlValue| {
            query(
                &configure(&[
                    ("method", "ldap".into()),
                    ("password", "x".into()),
                    ("cert", cert),
                ])
                .unwrap(),
            )
        };
        assert_eq!(https(false.into())["SSLVerification"], "NONE");
        assert_eq!(
            https("/etc/ssl/ca.pem".into())["SSLCertPath"],
            "/etc/ssl/ca.pem"
        );
        assert!(!https(true.into()).contains_key("SSLVerification"));
        assert!(configure(&[("cert", "/ca.pem".into())]).is_err());
    }

    #[test]
    fn disabled_verification_and_ignored_retries_warn() {
        let https = [("method", YmlValue::from("ldap")), ("password", "x".into())];
        let (result, warnings) =
            configure_with_warnings(&[https[0].clone(), https[1].clone(), ("cert", false.into())]);
        assert!(result.is_ok());
        assert!(
            warnings[0].contains("verification is disabled"),
            "{warnings:?}"
        );
        let (_, warnings) = configure_with_warnings(&[
            https[0].clone(),
            https[1].clone(),
            ("cert", false.into()),
            ("suppress_cert_warning", true.into()),
        ]);
        assert!(warnings.is_empty(), "{warnings:?}");
        let (_, warnings) = configure_with_warnings(&[("retries", 3.into())]);
        assert!(warnings[0].contains("'retries' is ignored"), "{warnings:?}");
    }

    #[test]
    fn values_cannot_inject_uri_options() {
        let builder = configure(&[
            ("user", "user@host".into()),
            ("database", "catalog&SSLVerification=NONE".into()),
        ])
        .unwrap();
        let query = query(&builder);
        assert_eq!(query["catalog"], "catalog&SSLVerification=NONE");
        assert!(!query.contains_key("SSLVerification"));
        assert_eq!(builder.username.as_deref(), Some("user@host"));
    }

    #[test]
    fn kerberos_requires_keytab_and_realm() {
        let builder = configure(&[
            ("method", "kerberos".into()),
            ("keytab", "/etc/dbt.keytab".into()),
            ("principal", "dbt@EXAMPLE.COM".into()),
            ("krb5_config", "/etc/krb5.conf".into()),
            ("service_name", "trino".into()),
            ("mutual_authentication", false.into()),
        ])
        .unwrap();
        let query = query(&builder);
        assert_eq!(query["KerberosEnabled"], "true");
        assert_eq!(query["KerberosKeytabPath"], "/etc/dbt.keytab");
        assert_eq!(query["KerberosPrincipal"], "dbt");
        assert_eq!(query["KerberosRealm"], "EXAMPLE.COM");
        assert_eq!(query["KerberosConfigPath"], "/etc/krb5.conf");
        assert_eq!(query["KerberosRemoteServiceName"], "trino");
        assert!(
            configure(&[("method", "kerberos".into()), ("principal", "dbt@X".into())]).is_err()
        );
        assert!(
            configure(&[
                ("method", "kerberos".into()),
                ("keytab", "/k".into()),
                ("principal", "dbt".into()),
            ])
            .is_err()
        );
    }

    #[test]
    fn unsupported_options_fail_with_reasons() {
        for method in ["certificate", "gssapi", "oauth", "oauth_console"] {
            let err = configure(&[("method", method.into())]).unwrap_err();
            assert!(err.msg().contains("not supported"), "{method}");
        }
        assert!(configure(&[("method", "magic".into())]).is_err());
        assert!(configure(&[("impersonation_user", "other".into())]).is_err());
        assert!(configure(&[("http_headers", yaml("{X-Foo: bar}"))]).is_err());
        assert!(configure(&[("password", "x".into())]).is_err());
    }

    #[test]
    fn incomplete_profiles_fail() {
        for key in ["host", "user", "database", "schema", "port"] {
            let mut config = profile();
            config.remove(YmlValue::from(key));
            assert!(
                TrinoAuth::new(Box::new(crate::NoopAuthWarningPrinter))
                    .configure(&AdapterConfig::new(config))
                    .is_err(),
                "{key}"
            );
        }
    }
}
