---
layout: default
---

# DNS-over-HTTPS with Firefox Nightly

[Firefox Nightly](https://www.mozilla.org/en-US/firefox/channel/desktop/) has started implementing a DOH client, known as [Trusted Recursive Resolver](https://bugzilla.mozilla.org/show_bug.cgi?id=1434852) (TRR).

Assuming there is a DOH server accessible at `https://dns.example.com/dns-query` (or see [how to set your own](nginx-dohhttpproxy-unbound-centos7.md)), it is now possible to start using DNS over HTTPS in Firefox by following those steps:

* go to `about:config`
* search for `network.trr`
* change `network.trr.uri` to `https://dns.example.com/dns-query`
* change `network.trr.mode` to `2` (use DOH, but fallback to native resolver)
* optionally, change `network.trr.bootstrapAddress` to the IP of the DOH server to avoid any bootstrapping issue. If you don't, Firefox will use the native resolver to get the DOH server IP.

[@bagder](https://twitter.com/bagder) has a gist with more details on those [network.trr parameters](https://gist.github.com/bagder/5e29101079e9ac78920ba2fc718aceec).

## Caveat
Due to [BUG#1440563 TRR::DohEncode should set RD bit](https://bugzilla.mozilla.org/show_bug.cgi?id=1440563), you would need to apply this [patch to force RD bit](https://gist.github.com/chantra/d29bf407fa731ab1078de4c56a54a05c) to `doh-httpproxy` or `doh-proxy` would refuse to answer the DNS queries.

The TL;DR is that you would fork the repo, apply the patch, push it to your repo, and then install from your repo with:

```
pip install git+https://github.com/{myuser}/doh-proxy.git
```

or if you have a separate branch:
```
pip install git+https://github.com/{myuser}/doh-proxy.git@mybranch
```
