# Changelog

## [Unreleased]
### Fixed
- proxy: handle empty ct parameter

### Changed
- proxies and stub will listen to ::1 by default.
- proxies better handle malformed DNS messages

## [0.0.2] - 2018-01-16
### Added
- Travis CI
- Support multiple query over the same HTTP2 connection.
- started adding some unittests to utils.py
- `dohprxy/httpproxy.py` a HTTP1 proxy to run as a reverse proxy backend.

### Changed
- code refactor between stub and client
- use logging modules instead of rogue prints
- stub and client now use the same StubServerProtocol as the base to perform
  queries.
- proxy: use logging module instead of print
- doc: improved documentation and provide example setups.

### Removed
- dependency on hyper package

### Fixed
- doh-proxy: properly import dohproxy.protocol
- doh-client: properly set entry_point


## 0.0.1 - 2018-01-11
### Added
- Proxy script `dohproxy/proxy.py`
- Stub script `dohproxy/stub.py`
- Test client script `dohproxy/client.py`
- setuptools' setup.py
- doc
- CHANGELOG.md and README.md

[Unreleased]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.1...v0.0.2
