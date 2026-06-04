<!--
Thanks for the contribution. Use the most relevant section and
delete the rest.
-->

## Type of change

- [ ] New scenario or scenario fix
- [ ] Client / wire-shape change
- [ ] Docs only (README, WALKTHROUGH, per-scenario)
- [ ] Tooling / CI / repo plumbing

## Summary

<!-- One paragraph: what changed and why. -->

## Test plan

- [ ] `docker compose up -d` is healthy after the change.
- [ ] `./scripts/walkthrough.sh` runs end to end without manual intervention.
- [ ] The scenario this PR touches still demonstrates its capability (cite the access-log / audit-log row in the PR body).

## Out-of-scope

- [ ] Any change to the proxy itself lives in
      [`soapbucket/sbproxy`](https://github.com/soapbucket/sbproxy)
      or
      [`soapbucket/sbproxy-enterprise`](https://github.com/soapbucket/sbproxy-enterprise),
      not here.
