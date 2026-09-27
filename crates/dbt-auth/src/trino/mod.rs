//! Trino profile validation and ADBC connection options.
//!
//! Profiles follow the dbt-trino v1 credential fields:
//! <https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/adapters/trino/connections.py>
//!
//! The ADBC Trino driver (<https://github.com/adbc-drivers/trino>) reads only its URI, user name
//! and password, and hands the URI to trino-go-client. Unless noted, every option below is a DSN
//! query parameter of trino-go-client v0.333.0, the version that driver release go/v0.5.3 pins:
//! <https://github.com/trinodb/trino-go-client/blob/v0.333.0/trino/trino.go>.

use crate::{AdapterConfig, Auth, AuthError, AuthWarningPrinter, auth_configure_pipeline};
use database::Builder as DatabaseBuilder;
use dbt_adbc::{Backend, database};
use dbt_yaml::Value as YmlValue;
use std::borrow::Cow;
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

/// Profile keys that are rejected when set. An empty string or mapping counts as unset, as
/// dbt-trino v1 ignores an empty impersonation_user, http_headers or starburst_url.
const UNSUPPORTED_FIELDS: [(&str, &str); 4] = [
    (
        "impersonation_user",
        "Trino 'impersonation_user' is not supported by the ADBC Trino driver",
    ),
    (
        "http_headers",
        "Trino 'http_headers' is not supported by the ADBC Trino driver",
    ),
    (
        "role",
        "Trino 'role' is not a dbt-trino profile field; use roles: {system: <role>} or \
         roles: {<catalog>: <role>}",
    ),
    (
        "starburst_url",
        "Starburst Data Discovery sync (starburst_url) is not supported by the dbt v2 Trino \
         adapter. Remove the starburst_* keys from the profile.",
    ),
];

/// One variant per supported dbt-trino `method`. Each variant carries the coordinator address
/// because the method decides the URI scheme, and the token and Kerberos options are URI
/// parameters.
#[derive(Debug)]
enum TrinoAuthIR<'a> {
    /// `method: none`: the user name with no credential, over HTTP unless `http_scheme: https`.
    None {
        host: &'a str,
        port: u16,
        http_scheme: &'a str,
        user: &'a str,
    },
    /// `method: ldap`: HTTP basic authentication over HTTPS.
    Ldap {
        host: &'a str,
        port: u16,
        user: &'a str,
        password: Cow<'a, str>,
    },
    /// `method: jwt`: a bearer token over HTTPS. The user name is optional.
    Jwt {
        host: &'a str,
        port: u16,
        user: Option<&'a str>,
        jwt_token: Cow<'a, str>,
    },
    /// `method: kerberos`: SPNEGO with a keytab over HTTPS.
    Kerberos {
        host: &'a str,
        port: u16,
        user: &'a str,
        keytab: &'a str,
        principal: &'a str,
        realm: &'a str,
        krb5_config: Cow<'a, str>,
        service_name: Option<&'a str>,
    },
}

impl<'a> TrinoAuthIR<'a> {
    fn apply(
        self,
        mut builder: DatabaseBuilder,
        _warning_printer: &dyn AuthWarningPrinter,
    ) -> Result<DatabaseBuilder, AuthError> {
        match self {
            Self::None {
                host,
                port,
                http_scheme,
                user,
            } => {
                builder.with_uri(coordinator_uri(http_scheme, host, port)?);
                builder.with_username(user);
            }
            Self::Ldap {
                host,
                port,
                user,
                password,
            } => {
                builder.with_uri(coordinator_uri("https", host, port)?);
                builder.with_username(user);
                builder.with_password(password);
            }
            Self::Jwt {
                host,
                port,
                user,
                jwt_token,
            } => {
                let mut uri = coordinator_uri("https", host, port)?;
                uri.query_pairs_mut().append_pair("accessToken", &jwt_token);
                builder.with_uri(uri);
                if let Some(user) = user {
                    builder.with_username(user);
                }
            }
            Self::Kerberos {
                host,
                port,
                user,
                keytab,
                principal,
                realm,
                krb5_config,
                service_name,
            } => {
                let mut uri = coordinator_uri("https", host, port)?;
                {
                    let mut query = uri.query_pairs_mut();
                    query
                        .append_pair("KerberosEnabled", "true")
                        .append_pair("KerberosKeytabPath", keytab)
                        .append_pair("KerberosPrincipal", principal)
                        .append_pair("KerberosRealm", realm)
                        .append_pair("KerberosConfigPath", &krb5_config);
                    if let Some(service_name) = service_name {
                        query.append_pair("KerberosRemoteServiceName", service_name);
                    }
                }
                builder.with_uri(uri);
                builder.with_username(user);
            }
        }
        Ok(builder)
    }
}

/// `<scheme>://<host>:<port>/` with no user information: the driver takes the user name and
/// password as separate options.
fn coordinator_uri(scheme: &str, host: &str, port: u16) -> Result<Url, AuthError> {
    let mut uri = Url::parse("https://localhost").expect("valid constant URI");
    uri.set_scheme(scheme)
        .map_err(|_| AuthError::config("Invalid Trino HTTP scheme"))?;
    uri.set_host(Some(host)).map_err(|_| invalid_host(host))?;
    uri.set_port(Some(port))
        .map_err(|_| AuthError::config("Invalid Trino port"))?;
    Ok(uri)
}

/// `host` must be a bare host name or a bracketed IPv6 literal. `Url::set_host` keeps only the
/// text before a ':', so `localhost:9999` would silently use `port` and `https://trino` would
/// become the host `https`. This differs from dbt-trino v1, whose trino-python-client also
/// accepts a URL such as `https://trino:8443` and lets its scheme and port override
/// `http_scheme` and `port`:
/// <https://github.com/trinodb/trino-python-client/blob/0.340.0/trino/dbapi.py#L171-L240>
fn parse_host(config: &AdapterConfig) -> Result<&str, AuthError> {
    let host = required(config, "host")?;
    let ipv6_literal = host.starts_with('[') && host.ends_with(']');
    if host.contains('/') || (host.contains(':') && !ipv6_literal) {
        return Err(invalid_host(host));
    }
    Ok(host)
}

fn invalid_host(host: &str) -> AuthError {
    AuthError::config(format!(
        "Trino 'host' must be a host name only, for example trino.example.com. Put the port in \
         'port' and the scheme in 'http_scheme'. Got: '{host}'"
    ))
}

fn parse_auth<'a>(
    config: &'a AdapterConfig,
    _warning_printer: &dyn AuthWarningPrinter,
) -> Result<TrinoAuthIR<'a>, AuthError> {
    let host = parse_host(config)?;
    let port = config
        .get_string("port")
        .and_then(|value| value.parse::<u16>().ok())
        .filter(|port| *port != 0)
        .ok_or_else(|| AuthError::config("Trino requires a port between 1 and 65535"))?;

    for key in [
        "method",
        "http_scheme",
        "user",
        "timezone",
        "keytab",
        "principal",
        "krb5_config",
        "service_name",
    ] {
        if config.get(key).is_some_and(|value| !value.is_null()) && config.get_str(key).is_none() {
            return Err(AuthError::config(format!("Trino '{key}' must be a string")));
        }
    }
    if let Some((_, reason)) = UNSUPPORTED_FIELDS.iter().find(|(key, _)| {
        config.get(key).is_some_and(|value| match value {
            YmlValue::Null(..) => false,
            YmlValue::String(text, ..) => !text.is_empty(),
            YmlValue::Mapping(mapping, ..) => !mapping.is_empty(),
            _ => true,
        })
    }) {
        return Err(AuthError::config(*reason));
    }

    let method = config.get_str("method").unwrap_or("none");
    if let Some((_, reason)) = UNSUPPORTED_METHODS.iter().find(|(m, _)| *m == method) {
        return Err(AuthError::config(format!(
            "Trino method {method}: {reason}"
        )));
    }
    // dbt-trino v1 forces HTTPS for authenticated methods and defaults to HTTP otherwise.
    let http_scheme = config.get_str("http_scheme");
    let user = non_empty(config, "user");
    match method {
        "none" => {
            let http_scheme = match http_scheme {
                None => "http",
                Some(scheme @ ("http" | "https")) => scheme,
                Some(_) => {
                    return Err(AuthError::config(
                        "Trino 'http_scheme' must be http or https",
                    ));
                }
            };
            if non_empty_text(config, "password").is_some() {
                return Err(AuthError::config("A Trino password requires method ldap"));
            }
            Ok(TrinoAuthIR::None {
                host,
                port,
                http_scheme,
                user: user.ok_or_else(|| missing("user"))?,
            })
        }
        "ldap" | "jwt" | "kerberos" if !matches!(http_scheme, None | Some("https")) => Err(
            AuthError::config(format!("Trino method {method} requires http_scheme: https")),
        ),
        "ldap" => Ok(TrinoAuthIR::Ldap {
            host,
            port,
            user: user.ok_or_else(|| missing("user"))?,
            password: non_empty_text(config, "password")
                .ok_or_else(|| AuthError::config("Trino method ldap requires a password"))?,
        }),
        "jwt" => Ok(TrinoAuthIR::Jwt {
            host,
            port,
            user,
            jwt_token: non_empty_text(config, "jwt_token")
                .ok_or_else(|| AuthError::config("Trino method jwt requires jwt_token"))?,
        }),
        "kerberos" => parse_kerberos(config, host, port, user.ok_or_else(|| missing("user"))?),
        _ => Err(AuthError::config(format!(
            "Unknown Trino method '{method}'; supported methods are none, ldap, jwt and kerberos"
        ))),
    }
}

/// `method: kerberos` with a keytab. dbt-trino v1 also accepts a ticket cache, which the driver
/// cannot use.
fn parse_kerberos<'a>(
    config: &'a AdapterConfig,
    host: &'a str,
    port: u16,
    user: &'a str,
) -> Result<TrinoAuthIR<'a>, AuthError> {
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
    Ok(TrinoAuthIR::Kerberos {
        host,
        port,
        user,
        keytab,
        principal,
        realm,
        krb5_config: krb5_config_path(
            non_empty(config, "krb5_config"),
            std::env::var("KRB5_CONFIG").ok(),
        ),
        service_name: non_empty(config, "service_name"),
    })
}

/// dbt-trino v1 exports the profile's `krb5_config` as KRB5_CONFIG for the Kerberos library,
/// which otherwise reads KRB5_CONFIG or /etc/krb5.conf. trino-go-client reads no environment
/// variable, so the same path is resolved here.
fn krb5_config_path(profile_path: Option<&str>, env_path: Option<String>) -> Cow<'_, str> {
    match (profile_path, env_path) {
        (Some(path), _) => Cow::Borrowed(path),
        (None, Some(path)) => Cow::Owned(path),
        (None, None) => Cow::Borrowed("/etc/krb5.conf"),
    }
}

/// Catalog, schema, session settings and TLS, appended after the authentication parameters.
fn apply_connection_args(
    config: &AdapterConfig,
    mut builder: DatabaseBuilder,
    warning_printer: &dyn AuthWarningPrinter,
) -> Result<DatabaseBuilder, AuthError> {
    let catalog = required(config, "database")?;
    let schema = required(config, "schema")?;
    let uri = builder
        .uri
        .as_mut()
        .expect("TrinoAuthIR::apply sets the coordinator URI");
    let https = uri.scheme() == "https";
    {
        let mut query = uri.query_pairs_mut();
        query
            .append_pair("catalog", catalog)
            .append_pair("schema", schema)
            .append_pair(
                "source",
                &format!("{SOURCE_PREFIX}{}", env!("CARGO_PKG_VERSION")),
            );
        if let Some(roles) = string_map(config, "roles")? {
            query.append_pair("roles", &roles);
        }
        if let Some(properties) = string_map(config, "session_properties")? {
            query.append_pair("session_properties", &properties);
        }
        if let Some(tags) = client_tags(config)? {
            query.append_pair("clientTags", &tags);
        }
        if let Some(timezone) = non_empty(config, "timezone") {
            // trino-go-client reads `timezone` from v0.336.0 on. With driver go/v0.5.3
            // (v0.333.0), the session keeps the server time zone.
            query.append_pair("timezone", timezone);
        }
        if let Some(timeout) = query_timeout(config)? {
            query.append_pair("query_timeout", &timeout);
        }
        if let Some(enabled) = bool_field(config, "prepared_statements_enabled")? {
            // dbt-trino v1 inlines bindings on the client when this is false (connections.py
            // L590-L595). explicitPrepare only matters for a query with arguments, and dbt v2
            // renders bindings as SQL literals, so the value has no visible effect.
            query.append_pair("explicitPrepare", &enabled.to_string());
        }
        // Without `cert`, the driver verifies the server against the system trust store. This
        // differs from dbt-trino v1, which verifies only if `cert` or the
        // `require_certificate_validation` behavior flag (default False) is set:
        // https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/adapters/trino/connections.py#L687-L692
        match (https, config.get("cert")) {
            (_, None | Some(YmlValue::Null(..))) | (true, Some(YmlValue::Bool(true, ..))) => {}
            (true, Some(YmlValue::Bool(false, ..))) => {
                // dbt-trino v1 also warns unless `suppress_cert_warning` is set. dbt builds every
                // auth backend with NoopAuthWarningPrinter (auth_for_backend), so this warning
                // and the `retries` one below are not shown until dbt wires a real printer.
                if bool_field(config, "suppress_cert_warning")? != Some(true) {
                    warning_printer.warn(
                        "Trino TLS certificate verification is disabled (cert: false); set \
                         `cert` to a CA bundle path instead",
                    );
                }
                // The driver reads this parameter itself; trino-go-client does not.
                query.append_pair("SSLVerification", "NONE");
            }
            (true, Some(YmlValue::String(path, ..))) if !path.is_empty() => {
                query.append_pair("SSLCertPath", path);
            }
            (false, Some(_)) => {
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
    }
    if config.get("retries").is_some_and(|value| !value.is_null()) {
        // Accepted for dbt-trino v1 profile compatibility; v1 passes it to trino-python-client
        // as `max_attempts`.
        warning_printer.warn(
            "Trino 'retries' is ignored: the ADBC Trino driver has no client-side retry setting",
        );
    }
    Ok(builder)
}

/// trino-go-client parses `query_timeout` as a Go duration; a plain number means seconds. Zero is
/// rejected because trino-go-client would cancel every query as soon as it starts. Without the
/// key, the driver stops a query after `trino.DefaultQueryTimeout` (10h); dbt-trino v1 has no
/// client-side query timeout.
fn query_timeout(config: &AdapterConfig) -> Result<Option<Cow<'_, str>>, AuthError> {
    let Some(timeout) = config
        .get_string("query_timeout")
        .filter(|timeout| !timeout.is_empty())
    else {
        return Ok(None);
    };
    let seconds = is_decimal(&timeout);
    if !seconds && !is_go_duration(&timeout) {
        return Err(AuthError::config(format!(
            "Trino 'query_timeout' must be a number of seconds or a duration such as 300s, 30m \
             or 1h; got '{timeout}'"
        )));
    }
    if !timeout.contains(|c: char| matches!(c, '1'..='9')) {
        return Err(AuthError::config(
            "Trino 'query_timeout' must be greater than zero; remove it to use the driver \
             default of 10h",
        ));
    }
    Ok(Some(if seconds {
        Cow::Owned(format!("{timeout}s"))
    } else {
        timeout
    }))
}

/// Whether `value` is an unsigned decimal number, for example `300`, `1.5` or `.5`.
fn is_decimal(value: &str) -> bool {
    value.contains(|c: char| c.is_ascii_digit())
        && value.matches('.').count() <= 1
        && value.chars().all(|c| c.is_ascii_digit() || c == '.')
}

/// Whether `value` is an unsigned duration in Go's `time.ParseDuration` syntax, for example
/// `90s`, `1h30m` or `1.5h`.
fn is_go_duration(value: &str) -> bool {
    let mut rest = value;
    loop {
        let number_len = rest
            .find(|c: char| !c.is_ascii_digit() && c != '.')
            .unwrap_or(rest.len());
        let (number, tail) = rest.split_at(number_len);
        let Some(unit) = ["ns", "us", "ms", "s", "m", "h"]
            .into_iter()
            .find(|unit| tail.starts_with(unit))
        else {
            return false;
        };
        if !is_decimal(number) {
            return false;
        }
        rest = &tail[unit.len()..];
        if rest.is_empty() {
            return true;
        }
    }
}

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
        auth_configure_pipeline!(self, &config, parse_auth, apply_connection_args)
    }
}

fn missing(key: &str) -> AuthError {
    AuthError::config(format!("Trino requires '{key}' in the profile"))
}

fn non_empty<'a>(config: &'a AdapterConfig, key: &str) -> Option<&'a str> {
    config.get_str(key).filter(|value| !value.is_empty())
}

/// Like `non_empty`, but a YAML number or boolean is also taken as text. Secrets are read this
/// way, as in the Exasol and ClickHouse backends.
fn non_empty_text<'a>(config: &'a AdapterConfig, key: &str) -> Option<Cow<'a, str>> {
    config.get_string(key).filter(|value| !value.is_empty())
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
    fn method_none_may_use_https() {
        let builder = configure(&[
            ("http_scheme", "https".into()),
            ("cert", "/etc/ssl/ca.pem".into()),
        ])
        .unwrap();
        assert!(uri_value(&builder).starts_with("https://trino.example.test:8443/"));
        assert_eq!(query(&builder)["SSLCertPath"], "/etc/ssl/ca.pem");
        assert_eq!(builder.username.as_deref(), Some("test_user"));
        assert_eq!(builder.password, None);
    }

    #[test]
    fn http_scheme_must_be_http_or_https() {
        for scheme in ["ftp", "HTTPS", ""] {
            let err = configure(&[("http_scheme", scheme.into())]).unwrap_err();
            assert_eq!(err.msg(), "Trino 'http_scheme' must be http or https");
            let err = configure(&[
                ("method", "ldap".into()),
                ("password", "x".into()),
                ("http_scheme", scheme.into()),
            ])
            .unwrap_err();
            assert_eq!(err.msg(), "Trino method ldap requires http_scheme: https");
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
        assert_eq!(builder.username.as_deref(), Some("test_user"));
        let builder = configure(&[
            ("method", "jwt".into()),
            ("jwt_token", "abc.def.ghi".into()),
            ("user", "".into()),
        ])
        .unwrap();
        assert_eq!(builder.username, None);
        assert!(configure(&[("method", "jwt".into())]).is_err());
    }

    #[test]
    fn secrets_accept_yaml_numbers() {
        let builder =
            configure(&[("method", "ldap".into()), ("password", 12345678.into())]).unwrap();
        assert_eq!(builder.password.as_deref(), Some("12345678"));
        let builder =
            configure(&[("method", "jwt".into()), ("jwt_token", 12345678.into())]).unwrap();
        assert_eq!(query(&builder)["accessToken"], "12345678");
        // Other text fields stay strict, as dbt-trino v1 declares them `str`.
        let err = configure(&[("user", 12345678.into())]).unwrap_err();
        assert_eq!(err.msg(), "Trino 'user' must be a string");
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
    fn query_timeout_takes_seconds_or_a_go_duration() {
        for (timeout, expected) in [
            (YmlValue::from(300), "300s"),
            ("300".into(), "300s"),
            ("1.5".into(), "1.5s"),
            // An unquoted decimal is a YAML float.
            (yaml("1.5"), "1.5s"),
            (yaml("2.0"), "2.0s"),
            ("300s".into(), "300s"),
            ("30m".into(), "30m"),
            ("1h30m".into(), "1h30m"),
            ("500ms".into(), "500ms"),
            ("1.5h".into(), "1.5h"),
        ] {
            let builder = configure(&[("query_timeout", timeout)]).unwrap();
            assert_eq!(query(&builder)["query_timeout"], expected);
        }
        for timeout in ["5 minutes", "30M", "1h30", "-5m", "1.2.3s", "1.2.3", "ms"] {
            let err = configure(&[("query_timeout", timeout.into())]).unwrap_err();
            assert_eq!(
                err.msg(),
                format!(
                    "Trino 'query_timeout' must be a number of seconds or a duration such as \
                     300s, 30m or 1h; got '{timeout}'"
                )
            );
        }
        // The profile keeps any YAML value for query_timeout, so other types end up here too.
        for (timeout, text) in [
            (yaml("-1.5"), "-1.5"),
            (yaml("true"), "true"),
            (yaml("[300]"), "- 300"),
        ] {
            let err = configure(&[("query_timeout", timeout)]).unwrap_err();
            assert_eq!(
                err.msg(),
                format!(
                    "Trino 'query_timeout' must be a number of seconds or a duration such as \
                     300s, 30m or 1h; got '{text}'"
                )
            );
        }
        for timeout in [
            YmlValue::from(0),
            yaml("0.0"),
            "0".into(),
            "0.0".into(),
            "0s".into(),
        ] {
            let err = configure(&[("query_timeout", timeout)]).unwrap_err();
            assert_eq!(
                err.msg(),
                "Trino 'query_timeout' must be greater than zero; remove it to use the driver \
                 default of 10h"
            );
        }
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
    fn host_must_be_a_bare_host_name() {
        for host in [
            "https://trino.example.test",
            "trino.example.test:9999",
            "trino.example.test/",
            "[::1]:8443",
            "user@trino.example.test",
            "trino example",
        ] {
            let err = configure(&[("host", host.into())]).unwrap_err();
            assert_eq!(
                err.msg(),
                format!(
                    "Trino 'host' must be a host name only, for example trino.example.com. Put \
                     the port in 'port' and the scheme in 'http_scheme'. Got: '{host}'"
                )
            );
        }
        for (host, origin) in [
            ("10.0.0.5", "http://10.0.0.5:8443/"),
            ("[::1]", "http://[::1]:8443/"),
        ] {
            let uri = uri_value(&configure(&[("host", host.into())]).unwrap());
            assert!(uri.starts_with(origin), "{uri}");
        }
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
    fn kerberos_rejects_options_the_driver_lacks() {
        let kerberos = [
            ("method", YmlValue::from("kerberos")),
            ("keytab", "/etc/dbt.keytab".into()),
            ("principal", "dbt@EXAMPLE.COM".into()),
            ("krb5_config", "/etc/krb5.conf".into()),
        ];
        for (key, value) in [
            ("hostname_override", YmlValue::from("trino.internal")),
            ("force_preemptive", true.into()),
            ("delegate", true.into()),
            ("mutual_authentication", true.into()),
            ("mutual_authentication", "REQUIRED".into()),
        ] {
            let mut pairs = kerberos.to_vec();
            pairs.push((key, value));
            assert_eq!(
                configure(&pairs).unwrap_err().msg(),
                format!("Trino Kerberos option '{key}' is not supported by the ADBC Trino driver")
            );
        }
        // The dbt-trino v1 defaults, which leave these options off, are accepted.
        for (key, value) in [
            ("force_preemptive", YmlValue::from(false)),
            ("delegate", false.into()),
            ("mutual_authentication", false.into()),
            ("mutual_authentication", "DISABLED".into()),
        ] {
            let mut pairs = kerberos.to_vec();
            pairs.push((key, value));
            assert!(configure(&pairs).is_ok(), "{key}");
        }
    }

    #[test]
    fn krb5_config_prefers_profile_then_environment() {
        let env = || Some("/env/krb5.conf".to_string());
        assert_eq!(
            krb5_config_path(Some("/profile/krb5.conf"), env()),
            "/profile/krb5.conf"
        );
        assert_eq!(krb5_config_path(None, env()), "/env/krb5.conf");
        assert_eq!(krb5_config_path(None, None), "/etc/krb5.conf");
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
        // An empty string or mapping counts as unset.
        for (key, value) in [
            ("impersonation_user", YmlValue::from("")),
            ("role", "".into()),
            ("http_headers", yaml("{}")),
        ] {
            assert!(configure(&[(key, value)]).is_ok(), "{key}");
        }
    }

    #[test]
    fn role_points_to_roles() {
        assert_eq!(
            configure(&[("role", "admin".into())]).unwrap_err().msg(),
            "Trino 'role' is not a dbt-trino profile field; use roles: {system: <role>} or \
             roles: {<catalog>: <role>}"
        );
    }

    #[test]
    fn starburst_data_discovery_sync_is_rejected() {
        let starburst_fields = [
            ("starburst_client_id", YmlValue::from("client")),
            ("starburst_metadata_failure_strategy", "fail".into()),
            ("starburst_max_column_batch_size", 50.into()),
        ];
        // Without a `starburst_url`, dbt-trino v1 does not sync either.
        assert!(configure(&starburst_fields).is_ok());
        assert!(configure(&[("starburst_url", "".into())]).is_ok());

        let mut with_url = starburst_fields.to_vec();
        with_url.push(("starburst_url", "https://starburst.example.test".into()));
        assert_eq!(
            configure(&with_url).unwrap_err().msg(),
            "Starburst Data Discovery sync (starburst_url) is not supported by the dbt v2 Trino \
             adapter. Remove the starburst_* keys from the profile."
        );
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

    #[test]
    fn port_must_be_between_1_and_65535() {
        for port in [
            YmlValue::from(0),
            65536.into(),
            (-1).into(),
            "abc".into(),
            "".into(),
        ] {
            let err = configure(&[("port", port)]).unwrap_err();
            assert_eq!(err.msg(), "Trino requires a port between 1 and 65535");
        }
        for port in [YmlValue::from(1), 65535.into(), "443".into()] {
            assert!(configure(&[("port", port)]).is_ok());
        }
    }

    // The full_uri_for_* tests compare the whole URI: query() keeps the last value of a repeated
    // parameter, but trino-go-client reads the first one (url.Values.Get).
    const SOURCE: &str = concat!("source=dbt-trino-", env!("CARGO_PKG_VERSION"));

    #[test]
    fn full_uri_for_method_none() {
        let builder = configure(&[
            ("roles", yaml("{hive: admin, system: ALL}")),
            (
                "session_properties",
                yaml("{query_max_run_time: 5m, retry_count: 2}"),
            ),
            ("client_tags", yaml("[etl, nightly]")),
            ("timezone", "UTC".into()),
            ("query_timeout", 300.into()),
            ("prepared_statements_enabled", false.into()),
        ])
        .unwrap();
        assert_eq!(
            uri_value(&builder),
            format!(
                "http://trino.example.test:8443/?catalog=iceberg&schema=analytics&{SOURCE}\
                 &roles=hive%3Aadmin%3Bsystem%3AALL\
                 &session_properties=query_max_run_time%3A5m%3Bretry_count%3A2\
                 &clientTags=etl%2Cnightly&timezone=UTC&query_timeout=300s&explicitPrepare=false"
            )
        );
    }

    #[test]
    fn full_uri_for_ldap() {
        let builder = configure(&[
            ("method", "ldap".into()),
            ("password", "p@ss:word&SSL=false".into()),
            ("cert", "/etc/ssl/ca.pem".into()),
        ])
        .unwrap();
        assert_eq!(
            uri_value(&builder),
            format!(
                "https://trino.example.test:8443/?catalog=iceberg&schema=analytics&{SOURCE}\
                 &SSLCertPath=%2Fetc%2Fssl%2Fca.pem"
            )
        );
    }

    #[test]
    fn full_uri_for_jwt() {
        let builder = configure(&[
            ("method", "jwt".into()),
            ("jwt_token", "abc.def.ghi".into()),
            ("cert", false.into()),
        ])
        .unwrap();
        assert_eq!(
            uri_value(&builder),
            format!(
                "https://trino.example.test:8443/?accessToken=abc.def.ghi&catalog=iceberg\
                 &schema=analytics&{SOURCE}&SSLVerification=NONE"
            )
        );
    }

    #[test]
    fn full_uri_for_kerberos() {
        let builder = configure(&[
            ("method", "kerberos".into()),
            ("keytab", "/etc/dbt.keytab".into()),
            ("principal", "dbt@EXAMPLE.COM".into()),
            ("krb5_config", "/etc/krb5.conf".into()),
            ("service_name", "trino".into()),
        ])
        .unwrap();
        assert_eq!(
            uri_value(&builder),
            format!(
                "https://trino.example.test:8443/?KerberosEnabled=true\
                 &KerberosKeytabPath=%2Fetc%2Fdbt.keytab&KerberosPrincipal=dbt\
                 &KerberosRealm=EXAMPLE.COM&KerberosConfigPath=%2Fetc%2Fkrb5.conf\
                 &KerberosRemoteServiceName=trino&catalog=iceberg&schema=analytics&{SOURCE}"
            )
        );
    }
}
