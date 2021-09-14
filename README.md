# EnvProxy

`EnvProxy` provides a class used to query environmental variables with typehinting a conversion to basic Python types.
You can query your environment easily and keep your typehinting.

## Installation

Using `pip`:

```console
pip install env-proxy
```

Using `poetry`:

```console
poetry add env-proxy
```

## Example

```python
# Import EnvProxy
from env_proxy import EnvProxy

# Basic examples
## Environment variable "DATABASE_HOST"
database_host = EnvProxy.get_str("database-host")

## If you want the function to fail if the value does not exist, use methods with `_strict` suffix
database_nonsene = EnvProxy.get_str_strict("database-nonsense")
### ValueError: No value for key DATABASE_NONSENSE in environment

## Specify default for the (non-zero) variable "DATABASE_PORT"
database_port = EnvProxy.get_int("database-port") or 5432

# Specify custom prefix
class MyProxy(EnvProxy):
    env_prefix: Optional[str] = "MYAPP"
## Now all variables are expected to be prefixed with MYAPP_
database_host = EnvProxy.get_str("database-host")
### Searches for MYAPP_DATABASE_HOST variable
```
