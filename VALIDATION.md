# Verification record

## Combined two-round subscription — 2026-11-06

- 35 exact identities across 9 original sources: original 27 first, second-round 8 below, including the added Zhangzhong node after all original sources.
- 39 offline tests passed; ordering, protocol preservation, service routing and shared-CDN boundaries, Claude assets, Telegram native DC ranges, invalid-order rejection and publication retention are covered.
- All 35 selected identities were found in original subscriptions fetched during this session. The resulting full configuration passed Mihomo v1.19.33 `-t` validation.
- Full output includes 11 groups and 106 rules, fake-IP DNS and hostname sniffing; the client TUN switch is not set by the subscription.
- Deployment schedule remains `17,47 * * * *` (every 30 minutes). Fixed Gist filenames remain unchanged. Actual online publication is verified separately in the deployment-status record.

## Original initial offline verification

- Python: 3.12.14 (bundled interpreter); PyYAML: 6.0.3 installed only in `.deps/`.
- Offline unit tests: **27 passed**, 0 failures, 0 errors; final recorded run took 1.685 seconds.
- No real source URL or node credentials were provided to these tests. All network publication requests are mocked.
- The complete 27-node selector set was generated from positive `AS9929 observed` audit rows: 14 Zhangzhong, 8 Speedy, 3 Muacloud, 2 Xinghe; the negative `AS9929 not observed` EMO row is excluded.
- Tests cover exact selection, renamed/missing/duplicate identities, cross-source naming, preservation of all original protocol options and refreshed servers, malformed entries, source/network errors without credential leakage, HTTPS-only source handling, response bounds, safe YAML parsing, complete FlClash groups/rule, rejection of public gists, explicit secret gist creation, one-request multi-file gist updates, revision-free URLs, preservation of previous files, and uncertain network publication outcomes.
- Actions YAML was parsed separately and verified for `17 */6 * * *`, manual dispatch, `contents: read`, SHA-pinned actions, one isolated step receiving Secrets, and a status-only artifact path.
- The setup-python pinned action commit resolves to its public action descriptor.
- Public repository structure was inspected read-only using the recursive tree API at HEAD `2d240290af5df1abce6f2541dafa3aa2cb41eebf`; all existing files live under `proxy-sub/` and `sub/`; proposed new paths do not collide. No existing subscription file contents were read.
- No `git push`, remote write, gist creation, mihomo process, or repeated line-quality network test was performed.
- Live source synchronization and actual remote gist creation/update are not claimed by this offline verification. They require the supplied source environments and a valid gist token.

Reproduce the tests from this directory after installing requirements:

```powershell
python -m unittest discover -s tests -v
```

On this machine, the already-installed isolated dependency and bundled interpreter can be used without changing the global Python:

```powershell
$env:PYTHONPATH = (Join-Path $PWD '.deps')
& 'C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```
