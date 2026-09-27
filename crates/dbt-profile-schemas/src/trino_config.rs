use super::common::*;
use dbt_common::{ErrorCode, FsResult, fs_err};
use dbt_schemas::schemas::profiles::TrinoDbConfig;
use dbt_schemas::schemas::serde::StringOrInteger;

/// The dbt-trino `method` values, in prompt order. The method prompt is a Select field, which
/// holds a position in this list.
const METHODS: [&str; 4] = ["none", "ldap", "jwt", "kerberos"];

fn method_index(method: &str) -> Option<i64> {
    METHODS.iter().position(|m| *m == method).map(|i| i as i64)
}

impl InteractiveSetup for TrinoDbConfig {
    fn get_fields() -> Vec<ConfigField> {
        let selected =
            |method: &str| FieldValue::Integer(method_index(method).expect("a method in METHODS"));
        let when_method = |method: &str| FieldCondition::IfFieldEquals {
            field_name: "method".to_string(),
            value: selected(method),
        };
        let unless_method = |method: &str| FieldCondition::IfFieldNotEquals {
            field_name: "method".to_string(),
            value: selected(method),
        };
        vec![
            ConfigField {
                name: "host".to_string(),
                field_type: FieldType::Input {
                    default: Some("localhost".to_string()),
                },
                condition: FieldCondition::Always,
                prompt: "Host (Trino coordinator hostname)".to_string(),
                required: true,
            },
            ConfigField {
                name: "method".to_string(),
                field_type: FieldType::Select {
                    options: METHODS.iter().map(|m| m.to_string()).collect(),
                    default_index: 0,
                },
                condition: FieldCondition::Always,
                prompt: "Authentication method".to_string(),
                required: true,
            },
            // The default port follows the scheme: HTTP for method none, HTTPS otherwise (see
            // set_field).
            ConfigField {
                name: "port".to_string(),
                field_type: FieldType::Input {
                    default: Some("8080".to_string()),
                },
                condition: when_method("none"),
                prompt: "Port".to_string(),
                required: true,
            },
            ConfigField {
                name: "port".to_string(),
                field_type: FieldType::Input {
                    default: Some("8443".to_string()),
                },
                condition: unless_method("none"),
                prompt: "Port (usually 443 or 8443 for HTTPS)".to_string(),
                required: true,
            },
            ConfigField {
                name: "user".to_string(),
                field_type: FieldType::Input { default: None },
                condition: unless_method("jwt"),
                prompt: "User".to_string(),
                required: true,
            },
            // `user` is optional for method jwt, as in dbt-trino v1:
            // https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/adapters/trino/connections.py#L427-L432
            ConfigField {
                name: "user".to_string(),
                field_type: FieldType::Input { default: None },
                condition: when_method("jwt"),
                prompt: "User (optional)".to_string(),
                required: false,
            },
            ConfigField {
                name: "password".to_string(),
                field_type: FieldType::Password,
                condition: when_method("ldap"),
                prompt: "Password".to_string(),
                required: true,
            },
            ConfigField {
                name: "jwt_token".to_string(),
                field_type: FieldType::Password,
                condition: when_method("jwt"),
                prompt: "JWT token".to_string(),
                required: true,
            },
            ConfigField {
                name: "keytab".to_string(),
                field_type: FieldType::Input { default: None },
                condition: when_method("kerberos"),
                prompt: "Kerberos keytab path".to_string(),
                required: true,
            },
            ConfigField {
                name: "principal".to_string(),
                field_type: FieldType::Input { default: None },
                condition: when_method("kerberos"),
                prompt: "Kerberos principal (user@REALM)".to_string(),
                required: true,
            },
            ConfigField {
                name: "cert".to_string(),
                field_type: FieldType::Input { default: None },
                condition: unless_method("none"),
                prompt: "CA bundle path (optional; blank keeps the current setting, or uses the \
                         system trust store for a new profile)"
                    .to_string(),
                required: false,
            },
            ConfigField {
                name: "database".to_string(),
                field_type: FieldType::Input { default: None },
                condition: FieldCondition::Always,
                prompt: "Catalog (e.g. hive, iceberg, delta)".to_string(),
                required: true,
            },
            ConfigField {
                name: "schema".to_string(),
                field_type: FieldType::Input { default: None },
                condition: FieldCondition::Always,
                prompt: "Schema".to_string(),
                required: true,
            },
        ]
    }

    fn set_field(&mut self, field_name: &str, value: FieldValue) -> FsResult<()> {
        match field_name {
            "host" => {
                if let FieldValue::String(val) = value {
                    self.host = Some(val);
                }
            }
            "method" => {
                if let FieldValue::Integer(index) = value
                    && let Some(&method) = METHODS.get(index as usize)
                {
                    // dbt-trino v1 uses HTTPS for every method but none, which defaults to HTTP
                    // and also works over HTTPS:
                    // https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/adapters/trino/connections.py#L229-L236
                    if method != "none" {
                        self.http_scheme = Some("https".to_string());
                    } else if self.method.as_deref().is_some_and(|m| m != "none") {
                        // Switching to none: dbt-auth rejects a password, and a `cert` over
                        // HTTP, with method none.
                        self.http_scheme = Some("http".to_string());
                        self.password = None;
                        self.cert = None;
                    } else {
                        // A new profile gets HTTP; a method none profile being edited keeps its
                        // scheme.
                        self.http_scheme.get_or_insert_with(|| "http".to_string());
                    }
                    self.method = Some(method.to_string());
                }
            }
            "port" => match value {
                FieldValue::String(val) => {
                    if let Ok(port) = val.parse::<i64>() {
                        self.port = Some(StringOrInteger::Integer(port));
                    }
                }
                FieldValue::Integer(val) => {
                    self.port = Some(StringOrInteger::Integer(val));
                }
                _ => {}
            },
            "user" => {
                // A blank answer to the optional jwt prompt leaves `user` as it is.
                if let FieldValue::String(val) = value
                    && !val.is_empty()
                {
                    self.user = Some(val);
                }
            }
            "password" => {
                if let FieldValue::String(val) = value {
                    self.password = Some(val);
                }
            }
            "jwt_token" => {
                if let FieldValue::String(val) = value {
                    self.jwt_token = Some(val);
                }
            }
            "keytab" => {
                if let FieldValue::String(val) = value {
                    self.keytab = Some(val);
                }
            }
            "principal" => {
                if let FieldValue::String(val) = value {
                    self.principal = Some(val);
                }
            }
            "cert" => {
                // Blank keeps the system trust store, or the `cert` of the profile being edited.
                if let FieldValue::String(val) = value
                    && !val.is_empty()
                {
                    self.cert = Some(val.into());
                }
            }
            "database" => {
                if let FieldValue::String(val) = value {
                    self.database = Some(val);
                }
            }
            "schema" => {
                if let FieldValue::String(val) = value {
                    self.schema = Some(val);
                }
            }
            _ => {
                return Err(fs_err!(
                    ErrorCode::InvalidArgument,
                    "Unknown field: {}",
                    field_name
                ));
            }
        }
        Ok(())
    }

    fn get_field(&self, field_name: &str) -> Option<FieldValue> {
        let text = |value: &Option<String>| value.clone().map(FieldValue::String);
        match field_name {
            "host" => text(&self.host),
            // A position, so that editing a profile pre-selects its method.
            "method" => self
                .method
                .as_deref()
                .and_then(method_index)
                .map(FieldValue::Integer),
            // Text, so that editing a profile pre-fills the port prompt.
            "port" => self
                .port
                .as_ref()
                .map(|port| FieldValue::String(port.to_string())),
            "user" => text(&self.user),
            "password" => text(&self.password),
            "jwt_token" => text(&self.jwt_token),
            "keytab" => text(&self.keytab),
            "principal" => text(&self.principal),
            "cert" => self
                .cert
                .as_ref()
                .and_then(|cert| cert.as_str())
                .map(|path| FieldValue::String(path.to_string())),
            "database" => text(&self.database),
            "schema" => text(&self.schema),
            _ => None,
        }
    }

    fn is_field_set(&self, field_name: &str) -> bool {
        self.get_field(field_name).is_some()
    }
}

pub(crate) fn setup_trino_profile(
    existing_config: Option<&TrinoDbConfig>,
) -> FsResult<Box<TrinoDbConfig>> {
    let default_config = TrinoDbConfig::default();
    let mut config = ConfigProcessor::process_config(existing_config.or(Some(&default_config)))?;

    if config.threads.is_none() {
        config.threads = Some(StringOrInteger::Integer(4));
    }

    Ok(Box::new(config))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::headless::{adapter_fields, apply_values, build_profile_target, supported_adapters};
    use dbt_adapter_core::AdapterType;
    use dbt_schemas::schemas::profiles::DbConfig;
    use std::collections::HashMap;

    fn text(value: &str) -> FieldValue {
        FieldValue::String(value.to_string())
    }

    fn method(name: &str) -> FieldValue {
        FieldValue::Integer(method_index(name).unwrap())
    }

    fn apply(base: &TrinoDbConfig, answers: &[(&str, FieldValue)]) -> TrinoDbConfig {
        let values = answers
            .iter()
            .map(|(name, value)| (name.to_string(), value.clone()))
            .collect();
        apply_values(base, &values).unwrap()
    }

    /// The prompts that `dbt init` shows once `method_name` is chosen.
    fn prompts(method_name: &str) -> Vec<ConfigField> {
        let chosen = HashMap::from([("method".to_string(), method(method_name))]);
        TrinoDbConfig::get_fields()
            .into_iter()
            .filter(|field| {
                ConfigProcessor::should_show_field(field, &chosen, &TrinoDbConfig::default())
            })
            .collect()
    }

    fn prompt(method_name: &str, name: &str) -> ConfigField {
        prompts(method_name)
            .into_iter()
            .find(|field| field.name == name)
            .unwrap()
    }

    #[test]
    fn prompts_follow_the_chosen_method() {
        let names = |method_name| {
            prompts(method_name)
                .into_iter()
                .map(|field| field.name)
                .collect::<Vec<_>>()
                .join(" ")
        };
        assert_eq!(names("none"), "host method port user database schema");
        assert_eq!(
            names("ldap"),
            "host method port user password cert database schema"
        );
        assert_eq!(
            names("jwt"),
            "host method port user jwt_token cert database schema"
        );
        assert_eq!(
            names("kerberos"),
            "host method port user keytab principal cert database schema"
        );

        let port_default = |method_name| match prompt(method_name, "port").field_type {
            FieldType::Input { default } => default,
            field_type => panic!("expected an Input port prompt, got {field_type:?}"),
        };
        assert_eq!(port_default("none").as_deref(), Some("8080"));
        for method_name in ["ldap", "jwt", "kerberos"] {
            assert_eq!(port_default(method_name).as_deref(), Some("8443"));
            assert!(!prompt(method_name, "cert").required);
        }
        assert!(prompt("ldap", "user").required);
        assert!(!prompt("jwt", "user").required);
    }

    #[test]
    fn headless_answers_keep_only_the_chosen_method() {
        let answer_all = |method_name| {
            apply(
                &TrinoDbConfig::default(),
                &[
                    ("host", text("trino.example.com")),
                    ("method", method(method_name)),
                    ("port", text("8443")),
                    ("user", text("dbt")),
                    ("password", text("secret")),
                    ("jwt_token", text("token")),
                    ("keytab", text("/etc/dbt.keytab")),
                    ("principal", text("dbt@EXAMPLE.COM")),
                    ("cert", text("/etc/ssl/ca.pem")),
                    ("database", text("iceberg")),
                    ("schema", text("analytics")),
                ],
            )
        };
        let common = TrinoDbConfig {
            host: Some("trino.example.com".to_string()),
            port: Some(StringOrInteger::Integer(8443)),
            user: Some("dbt".to_string()),
            database: Some("iceberg".to_string()),
            schema: Some("analytics".to_string()),
            ..Default::default()
        };
        let https = |method_name: &str| TrinoDbConfig {
            method: Some(method_name.to_string()),
            http_scheme: Some("https".to_string()),
            cert: Some("/etc/ssl/ca.pem".into()),
            ..common.clone()
        };

        assert_eq!(
            answer_all("none"),
            TrinoDbConfig {
                method: Some("none".to_string()),
                http_scheme: Some("http".to_string()),
                ..common.clone()
            }
        );
        assert_eq!(
            answer_all("ldap"),
            TrinoDbConfig {
                password: Some("secret".to_string()),
                ..https("ldap")
            }
        );
        assert_eq!(
            answer_all("jwt"),
            TrinoDbConfig {
                jwt_token: Some("token".to_string()),
                ..https("jwt")
            }
        );
        assert_eq!(
            answer_all("kerberos"),
            TrinoDbConfig {
                keytab: Some("/etc/dbt.keytab".to_string()),
                principal: Some("dbt@EXAMPLE.COM".to_string()),
                ..https("kerberos")
            }
        );
    }

    #[test]
    fn blank_optional_answers_keep_the_current_value() {
        let jwt = apply(
            &TrinoDbConfig::default(),
            &[
                ("method", method("jwt")),
                ("user", text("")),
                ("cert", text("")),
            ],
        );
        assert_eq!((jwt.user, jwt.cert), (None, None));

        // `cert: false` has no text to pre-fill, so the prompt is blank when editing.
        let unverified = TrinoDbConfig {
            method: Some("ldap".to_string()),
            cert: Some(false.into()),
            ..Default::default()
        };
        assert_eq!(unverified.get_field("cert"), None);
        let edited = apply(
            &unverified,
            &[("method", method("ldap")), ("cert", text(""))],
        );
        assert_eq!(edited.cert, Some(false.into()));
    }

    #[test]
    fn editing_preselects_the_method_and_prefills_the_answers() {
        for (position, name) in METHODS.into_iter().enumerate() {
            let config = TrinoDbConfig {
                method: Some(name.to_string()),
                ..Default::default()
            };
            assert_eq!(
                config.get_field("method"),
                Some(FieldValue::Integer(position as i64))
            );
        }

        let edited = TrinoDbConfig {
            port: Some(StringOrInteger::Integer(443)),
            cert: Some("/etc/ssl/ca.pem".into()),
            ..Default::default()
        };
        assert_eq!(edited.get_field("port"), Some(text("443")));
        assert_eq!(edited.get_field("cert"), Some(text("/etc/ssl/ca.pem")));
    }

    #[test]
    fn choosing_none_keeps_https_only_for_a_method_none_profile() {
        // A profile without `method` uses none, as in dbt-trino v1.
        for current in [None, Some("none".to_string())] {
            let tls = TrinoDbConfig {
                method: current,
                http_scheme: Some("https".to_string()),
                cert: Some("/etc/ssl/ca.pem".into()),
                ..Default::default()
            };
            assert_eq!(
                apply(&tls, &[("method", method("none"))]),
                TrinoDbConfig {
                    method: Some("none".to_string()),
                    ..tls
                }
            );
        }

        let ldap = TrinoDbConfig {
            method: Some("ldap".to_string()),
            http_scheme: Some("https".to_string()),
            password: Some("secret".to_string()),
            cert: Some("/etc/ssl/ca.pem".into()),
            ..Default::default()
        };
        let none = apply(&ldap, &[("method", method("none"))]);
        assert_eq!(none.http_scheme.as_deref(), Some("http"));
        assert_eq!((none.password, none.cert), (None, None));
    }

    #[test]
    fn headless_setup_builds_a_trino_target() {
        assert!(supported_adapters().contains(&AdapterType::Trino));
        assert!(adapter_fields(AdapterType::Trino).is_ok());

        let values = HashMap::from([("method".to_string(), method("none"))]);
        let target = build_profile_target(AdapterType::Trino, "dev", &values).unwrap();
        let Some(DbConfig::Trino(config)) = target.outputs.get("dev") else {
            panic!("expected a Trino output, got {:?}", target.outputs);
        };
        assert_eq!(config.method.as_deref(), Some("none"));
        assert_eq!(config.threads, Some(StringOrInteger::Integer(4)));
    }
}
