# Key transformations

`EnvProxy` transforms each requested key into the actual env-var name
according to three flags set on the proxy:

| Option        | Default | Effect                                                  |
|---------------|---------|---------------------------------------------------------|
| `prefix`      | `None`  | Prepends `<prefix>_` to every key.                      |
| `uppercase`   | `True`  | Uppercases the resulting key.                           |
| `underscored` | `True`  | Replaces `-` with `_` in the resulting key.             |

## Example

```python
proxy = EnvProxy(prefix="myapp", uppercase=True, underscored=False)
proxy.get_any("var")  # looks up "MYAPP_VAR"
```

```python
proxy = EnvProxy(prefix="myapp")  # uppercase=True, underscored=True
proxy.get_any("api-token")  # looks up "MYAPP_API_TOKEN"
```

## Caching

The transformation is memoised — see
[Tune the key cache](../how-to/tune-key-cache.md) for the cache size
knob.
