# CR2SE Redundancy

CR2SE assumes failure. A peer may be offline, lose its storage, stop offering a
service, change future prices, or act dishonestly. Trust changes which peers a
requester selects; it does not remove those failure modes.

**One successful operation at one provider is one copy in one failure domain.
It is not redundant storage, reliable delivery, or a backup.** Applications
that need continued availability must arrange multiple independent service
agreements and must be able to recover using any surviving agreement.

This document defines a common reliability rule for CR2SE services. It does not
add a wire message or make providers coordinate, so it is compatible with
version 1 service implementations.

---

## 1. Independent agreements

Every service invocation has exactly one requester and one provider. Success
commits only that provider to the output and duration defined by the selected
service. It makes no statement about another identity, node, device, network,
or copy.

A **replica set** is a requester's local collection of independent agreements
that protect the same recoverable item. A replica set is not a CR2SE service,
identity, consensus group, or provider-side promise. No member of a replica set
may claim that another member accepted, retained, or returned an item unless it
has separately obtained and verified that provider's protocol result.

The requester chooses its desired replica count and independence policy. A
count alone is insufficient when several identities depend on the same machine,
operator, network, power supply, account, backing store, or encryption key.
CR2SE cannot prove that providers are operationally independent; provider
diversity is a local risk decision informed by observation and trust.

---

## 2. Application requirements

An application that describes data as **redundant**, **reliably persisted**, or
**reliably deliverable** must:

1. define a local target of at least two independently accepted agreements;
2. count an agreement only after that provider returns the service's complete
   successful result;
3. present the target and the number of currently confirmed, unexpired
   agreements separately;
4. never present a single agreement, an attempted operation, or a requested
   target as completed redundancy;
5. retain the identifiers, content hashes, expiration times, authorization
   material, and decryption keys needed to use each surviving agreement;
6. check or retrieve agreements independently and treat timeout or network
   failure as inconclusive rather than proof that another replica exists;
7. repair the replica set by creating a replacement agreement when confirmed
   copies fall below the local target; and
8. stagger checks and renewals where practical, so one temporary outage or
   missed deadline does not affect every copy at once.

An application may expose states such as:

```text
not redundant       confirmed agreements < 2
under-replicated     2 <= confirmed agreements < local target
target satisfied     confirmed agreements >= local target
at risk              checks, retrievals, or expiry times require repair
```

`target satisfied` is a report about observations, not a guarantee of future
availability. User interfaces should say which observations are stale and when
agreements expire.

---

## 3. Service-specific identity

Services determine when two agreements protect the same item:

- For [Storage](./Storage.md), each lease is one agreement. Replicas contain
  identical bytes and therefore have the same `contentHash` and `sizeBytes`,
  but have independently returned lease IDs from different provider
  identities.
- For [Messaging](./Messaging.md), each placement is one agreement. Replicas
  use the same sender-generated `messageId` and identical signed payload, but
  have independently returned placement IDs from different provider
  identities.

Two leases or placements at the same provider identity do not satisfy the
minimum independence rule. Multiple nodes operated by one identity may share
state and failure modes and are still one provider for this purpose.

Other services may define their own stable item identifier and recovery
condition. Unless such a service explicitly defines multi-provider semantics,
the common rule remains: one successful invocation proves only one provider's
agreement.

---

## 4. What the protocol cannot guarantee

CR2SE can authenticate provider identities, define exact service commitments,
and provide checks. It cannot guarantee that independently named identities
are controlled independently, that a chosen number of copies achieves a given
uptime, or that every provider will honor a commitment after catastrophic or
malicious failure.

Automatic provider-to-provider replication would not remove this limitation:
the requester would still need independently authenticated acceptance results
to distinguish completed copies from a promise to create them. Version 1
therefore keeps placement, verification, renewal, and repair under requester
control. A future service may automate orchestration, but it must report each
underlying provider agreement separately and must not turn a replication target
into evidence of completed redundancy.
