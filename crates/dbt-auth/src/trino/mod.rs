//! Trino profile validation and ADBC connection options.

use crate::{AdapterConfig, Auth, AuthError};
use dbt_adbc::{Backend, database};
use url::Url;

pub const BACKEND: Backend = Backend::Generic {
    library_name: "adbc_driver_trino",
    entrypoint: None,
};

pub struct TrinoAuth;

impl Auth for TrinoAuth {
    fn backend(&self) -> Backend {
        BACKEND
    }

    fn configure(&self, config: &AdapterConfig) -> Result<database::Builder, AuthError> {
        let required = |key| {
            config
                .get_str(key)
                .filter(|value| !value.is_empty())
                .ok_or_else(|| AuthError::config(format!("Trino requires '{key}' in the profile")))
        };
        let host = required("host")?;
        let user = required("user")?;
        let catalog = required("database")?;
        let schema = required("schema")?;
        for key in ["http_scheme", "method", "password", "role"] {
            if config.get(key).is_some_and(|value| !value.is_null())
                && config.get_str(key).is_none()
            {
                return Err(AuthError::config(format!("Trino '{key}' must be a string")));
            }
        }
        let scheme = config.get_str("http_scheme").unwrap_or("https");
        if !matches!(scheme, "http" | "https") {
            return Err(AuthError::config(
                "Trino 'http_scheme' must be http or https",
            ));
        }
        let port = config
            .get_string("port")
            .and_then(|value| value.parse::<u16>().ok())
            .filter(|port| *port != 0)
            .ok_or_else(|| AuthError::config("Trino requires a port between 1 and 65535"))?;
        let password = config.get_str("password");
        match config.get_str("method").unwrap_or("none") {
            "none" if password.is_none() => {}
            "ldap" if password.is_some_and(|value| !value.is_empty()) && scheme == "https" => {}
            "ldap" if scheme != "https" => {
                return Err(AuthError::config(
                    "Trino password authentication requires HTTPS",
                ));
            }
            "ldap" => return Err(AuthError::config("Trino method ldap requires a password")),
            "none" => return Err(AuthError::config("A Trino password requires method ldap")),
            _ => {
                return Err(AuthError::config(
                    "Supported Trino methods are none and ldap",
                ));
            }
        }
        if config.get_str("role").is_some() {
            return Err(AuthError::config(
                "Trino role selection is not supported by this adapter yet",
            ));
        }

        let mut uri = Url::parse("https://localhost").expect("valid constant URI");
        uri.set_scheme(scheme)
            .map_err(|_| AuthError::config("Invalid Trino HTTP scheme"))?;
        uri.set_host(Some(host))
            .map_err(|_| AuthError::config("Invalid Trino host"))?;
        uri.set_port(Some(port))
            .map_err(|_| AuthError::config("Invalid Trino port"))?;
        uri.set_username(user)
            .map_err(|_| AuthError::config("Invalid Trino user"))?;
        uri.set_password(password)
            .map_err(|_| AuthError::config("Invalid Trino password"))?;
        uri.query_pairs_mut()
            .append_pair("catalog", catalog)
            .append_pair("schema", schema);
        let mut builder = database::Builder::new(BACKEND);
        builder.with_parse_uri(uri.as_str())?;
        Ok(builder)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_options::uri_value;
    use dbt_yaml::Mapping;

    fn profile() -> Mapping {
        Mapping::from_iter([
            ("host".into(), "trino.example.test".into()),
            ("port".into(), 8443.into()),
            ("user".into(), "test_user".into()),
            ("database".into(), "iceberg".into()),
            ("schema".into(), "analytics".into()),
        ])
    }

    #[test]
    fn https_is_default_and_port_accepts_integer_or_string() {
        for port in [dbt_yaml::Value::from(8443), "8443".into()] {
            let mut config = profile();
            config.insert("port".into(), port);
            let builder = TrinoAuth.configure(&AdapterConfig::new(config)).unwrap();
            let uri = Url::parse(&uri_value(&builder)).unwrap();
            assert_eq!(uri.scheme(), "https");
            assert_eq!(uri.port(), Some(8443));
            assert_eq!(uri.username(), "test_user");
        }
    }

    #[test]
    fn password_over_http_is_rejected_without_echoing_it() {
        let mut config = profile();
        config.insert("http_scheme".into(), "http".into());
        config.insert("method".into(), "ldap".into());
        config.insert("password".into(), "test-secret".into());
        let err = TrinoAuth
            .configure(&AdapterConfig::new(config))
            .unwrap_err();
        assert!(err.msg().contains("requires HTTPS"));
        assert!(!format!("{err:?}").contains("test-secret"));
    }

    #[test]
    fn credentials_and_catalog_cannot_inject_uri_options() {
        let mut config = profile();
        config.insert("method".into(), "ldap".into());
        config.insert("user".into(), "user@host".into());
        config.insert("password".into(), "p@ss:word&SSL=false".into());
        config.insert("database".into(), "catalog&SSLVerification=NONE".into());
        let builder = TrinoAuth.configure(&AdapterConfig::new(config)).unwrap();
        let uri = Url::parse(&uri_value(&builder)).unwrap();
        assert_eq!(uri.host_str(), Some("trino.example.test"));
        assert_eq!(uri.query_pairs().count(), 2);
        assert_eq!(
            uri.query_pairs().next().unwrap().1,
            "catalog&SSLVerification=NONE"
        );
        assert!(!format!("{builder:?}").contains("p%40ss"));
    }

    #[test]
    fn incomplete_profiles_and_unknown_methods_fail() {
        for key in ["host", "user", "database", "schema", "port"] {
            let mut config = profile();
            config.remove(&dbt_yaml::Value::from(key));
            assert!(TrinoAuth.configure(&AdapterConfig::new(config)).is_err());
        }
        let mut config = profile();
        config.insert("method".into(), "oauth".into());
        assert!(TrinoAuth.configure(&AdapterConfig::new(config)).is_err());
    }
}
