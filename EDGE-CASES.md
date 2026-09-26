---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 0% - by hand -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

**What the log contains:** Commit timestamps occurring after the deployment timestamp due to asynchronous machine clock drift.

**What a default definition would have done:** Discarded the negative pairs entirely or resulted in invalid negative median lead times.

**Why the rule is defensible:** Clamping negative lead times to zero preserves valuable throughput data while accurately tracking infrastructure synchronization anomalies.

## E2 - a revert of a revert

**What the log contains:** A chain where a revert commit reverts an earlier revert commit, pointing back to the original work unit.

**What a default definition would have done:** Treated each revert action as a completely independent change incrementing delivery stats incorrectly.

**Why the rule is defensible:** Transitive resolution correctly identifies that undoing a rollback restores the original business change context.

## E3 - a hotfix that never touched main

**What the log contains:** Production deployments carrying commits originating from alternative release or hotfix branches.

**What a default definition would have done:** Filtered out all commits not residing explicitly on the main branch, underreporting true lead times.

**Why the rule is defensible:** Production code delivery matters regardless of branch naming conventions or repository workflow structures.

## E4 - a deployment with zero linked commits

**What the log contains:** Production deployment events executed with empty commit lists, such as infrastructure configuration bumps.

**What a default definition would have done:** Crashed due to division by zero or dropped deployments entirely from frequency calculations.

**Why the rule is defensible:** Operational frequency must account for all production touches, maintaining accurate deployment volume denominators.

## E5 - a deployment that failed and never recovered

**What the log contains:** Failed production deployments that lacked corresponding incident resolution events within the observation window.

**What a default definition would have done:** Artificially closed failures at window boundaries or dropped unrecovered deployments from failure metrics.

**Why the rule is defensible:** Open failures represent real unmitigated stability risks that must remain visible in operational counts without fabricated recovery data.

## E6 - overlapping incidents

**What the log contains:** Multiple active service incidents whose active time windows intersect concurrently.

**What a default definition would have done:** Merged overlapping incidents or incorrectly summed their individual durations.

**Why the rule is defensible:** Recovery performance must be measured per deployment failure independently to avoid masking concurrent cascading failures.

## Gaming demonstration

We manipulated the deployment frequency metric by injecting additional production deployment events while simultaneously delaying base deployment timestamps. This artificially inflates deployment frequency to satisfy the relative margin improvement while measurably degrading base work delivery lead times, perfectly demonstrating Goodhart Law in software delivery metrics.
