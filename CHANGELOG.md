# Changelog

## [Unreleased]
### Added
- Travis CI
- Support multiple query over the same HTTP2 connection.

### Changed
- code refactor between stub and client
- use logging modules instead of rogue prints
- stub and client now use the same StubServerProtocol as the base to perform
  queries.
- proxy: use logging module instead of print

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

[Unreleased]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.1...HEAD
