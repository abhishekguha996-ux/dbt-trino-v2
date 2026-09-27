use super::common::*;
use dbt_common::{ErrorCode, FsResult, fs_err};
use dbt_schemas::schemas::profiles::TrinoDbConfig;
use dbt_schemas::schemas::serde::StringOrInteger;

const METHODS: [&str; 4] = ["none", "ldap", "jwt", "kerberos"];

impl InteractiveSetup for TrinoDbConfig {
    fn get_fields() -> Vec<ConfigField> {
        let when_method = |method: &str| FieldCondition::IfFieldEquals {
            field_name: "method".to_string(),
            value: FieldValue::String(method.to_string()),
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
            ConfigField {
                name: "port".to_string(),
                field_type: FieldType::Input {
                    default: Some("8443".to_string()),
                },
                condition: FieldCondition::Always,
                prompt: "Port (8080 for local HTTP, usually 443 or 8443 for HTTPS)".to_string(),
                required: true,
            },
            ConfigField {
                name: "user".to_string(),
                field_type: FieldType::Input { default: None },
                condition: FieldCondition::Always,
                prompt: "User".to_string(),
                required: true,
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
        let text = match &value {
            FieldValue::String(val) => Some(val.clone()),
            FieldValue::Integer(val) => Some(val.to_string()),
            _ => None,
        };
        match field_name {
            "host" => self.host = text,
            "method" => {
                // dbt-trino v1 uses HTTP for method none and HTTPS otherwise.
                self.http_scheme = Some(
                    if text.as_deref() == Some("none") {
                        "http"
                    } else {
                        "https"
                    }
                    .to_string(),
                );
                self.method = text;
            }
            "port" => {
                self.port = text
                    .and_then(|val| val.parse::<i64>().ok())
                    .map(StringOrInteger::Integer);
            }
            "user" => self.user = text,
            "password" => self.password = text,
            "jwt_token" => self.jwt_token = text,
            "keytab" => self.keytab = text,
            "principal" => self.principal = text,
            "database" => self.database = text,
            "schema" => self.schema = text,
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
            "method" => text(&self.method),
            "port" => self.port.as_ref().map(|v| match v {
                StringOrInteger::String(s) => FieldValue::String(s.clone()),
                StringOrInteger::Integer(i) => FieldValue::Integer(*i),
            }),
            "user" => text(&self.user),
            "password" => text(&self.password),
            "jwt_token" => text(&self.jwt_token),
            "keytab" => text(&self.keytab),
            "principal" => text(&self.principal),
            "database" => text(&self.database),
            "schema" => text(&self.schema),
            _ => None,
        }
    }

    fn is_field_set(&self, field_name: &str) -> bool {
        self.get_field(field_name).is_some()
    }
}

pub fn setup_trino_profile(
    existing_config: Option<&TrinoDbConfig>,
) -> FsResult<Box<TrinoDbConfig>> {
    let default_config = TrinoDbConfig::default();
    let mut config = ConfigProcessor::process_config(existing_config.or(Some(&default_config)))?;

    if config.threads.is_none() {
        config.threads = Some(StringOrInteger::Integer(4));
    }

    Ok(Box::new(config))
}
