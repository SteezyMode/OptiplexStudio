## Purpose
What behavior or acceptance criterion does this change address? Link the issue or frozen Studio v1 gate.

## What changed
Briefly describe files/components. Distinguish packaged GTK code from host/Wolf experiments.

## Verification
- [ ] `make -f Makefile.studio check`
- [ ] `make -f Makefile.studio package`
- [ ] Isolated GTK/package verification
- [ ] Live integration checks where applicable (or state **not run**)

Include commands and results. A headless pass is not a GUI acceptance.

## Safety and compatibility
- [ ] No unrelated services or projects changed
- [ ] Project files, Codex sessions, config and settings preserved
- [ ] No new v1.0 release scope without approval
- [ ] Rollback and known remaining gaps documented

## Manual acceptance / evidence
What should a reviewer actually click, run or observe? Link logs or concise results without private data.
