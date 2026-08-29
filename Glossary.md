# CR2SE Glossary

This glossary defines the common vocabulary used across CR2SE specifications. A term has the same meaning in every layer unless a specification explicitly narrows it for a particular context. The detailed specification linked from an entry remains authoritative for protocol behavior and data formats.

## Core concepts

**CR2SE**
A peer-to-peer protocol in which identities exchange services for identity-issued credits. CR2SE defines networking, identity, cryptography, service discovery, service contracts, invocation, and local economic accounting. It does not define a global currency or central authority.

**CR2SE identity** (short form: **identity**)
A cryptographic identity consisting of an Ed25519 key pair and the CR2SE ID derived from its public key. An identity is independent of any person, machine, process, network address, or connection. One identity may operate through multiple nodes. See [Identity](./Identity.md).

**CR2SE ID**
The stable 256-bit identifier derived from a CR2SE identity's version, key algorithm, and public key. It identifies the identity; it is not a network address.

**CR2SE node** (short form: **node**)
A running implementation of CR2SE. A node operates as exactly one CR2SE identity, while the same identity may operate through multiple nodes.

**peer**
The remote CR2SE node or identity participating in an interaction, as determined by context. Prefer **node** when referring specifically to a running implementation and **identity** when referring to ownership, trust, credits, or authorization.

**CR2SE connection** (short form: **connection**)
A persistent network connection between two nodes. A connection is a communication channel, not an identity.

**Node API**
The interface through which an application controls its local CR2SE node. It is distinct from the peer-to-peer network protocol. The Node API may be embedded in the application or exposed through local IPC. See [Node API](./NodeApi.md).

## Boards and services

**Board**
A versioned, machine-readable advertisement of the services a Board publisher provides or wants, including offering-specific payment terms and metadata. A Board contains compact summaries; complete service definitions are retrieved separately. See [Board](./Board.md).

**Board publisher**
The CR2SE identity that publishes a Board. A Board belongs to the identity, even when several nodes operate as that identity.

**service**
A versioned operation one CR2SE identity performs for another identity in exchange for credits. A service defines its input, output, success and failure behavior, and check. See [Services](./Services.md).

**offering**
One Board entry advertising a particular service and its terms. An offering is identified by an ID unique within its Board. Multiple offerings may refer to the same service version while differing in price, capacity, duration, or other terms.

**provided service**
An offering in `providedServices` that the Board publisher is willing to perform for another identity. The term describes service direction, not credit direction.

**wanted service**
An offering in `wantedServices` that the Board publisher wants another identity to perform for it. The term describes service direction, not credit direction.

**service requester** (short form: **requester**)
The identity that asks for a service during one invocation and pays the agreed price. This role is scoped to that invocation and is independent of who opened the network connection.

**service provider** (short form: **provider**)
The identity that performs a service during one invocation and returns its output. This role is scoped to that invocation and is independent of who published the selected offering.

**service definition**
The separately retrievable, typed contract for an offering. It identifies the service and version and defines the operation's input, output, check, and semantic behavior.

**invocation**
One attempt by a service requester to use a selected offering. The requester and provider agree on the offering, credit issuer, and price before execution.

**check**
A service-defined procedure through which the requester may evaluate whether the promised service was provided. A check can pass, fail, or be inconclusive; its result does not automatically reverse a credit payment.

**storage lease**
An accepted CR2SE Storage agreement binding immutable bytes, a requester identity, a provider identity, and an expiration time. Retrieval and renewal are separately charged using current provider offerings, while possession checks sample availability during the active lease. See [Storage](./Storage.md).

**message placement**
An accepted CR2SE Messaging agreement in which one provider retains one
sender-signed message for one recipient identity until recovery, removal, or
expiration. Several placements may contain replicas of the same message. See
[Messaging](./Messaging.md).

**discovery record**
A canonical, signed, expiring identity-address, public-share-availability, or
published-trust statement that peers may validate and copy independently. See
[Discovery](./Discovery.md).

**discovery index**
One identity's local collection of discovery records and identities learned
from authenticated connections. It is not a global directory or membership
list. See [Discovery](./Discovery.md).

**indexer**
An identity that provides the CR2SE Discovery service using a discovery index.

## Credits and trust

**credit**
A non-negative integer unit issued by one CR2SE identity. Credits from different issuers are distinct and need not have equal value. A credit has practical value only to the extent that its issuer or another identity chooses to accept it. See [Ledger](./Ledger.md).

**credit issuer** (short form: **issuer**)
The CR2SE identity that creates a credit and controls the terms under which that credit is recognized or accepted.

**credit owner** (short form: **owner**)
The CR2SE identity currently recorded as possessing credits issued by another identity. Ownership is represented in local ledger records and those records may disagree between identities.

**local ledger** (short form: **ledger**)
An identity's local record of owned credits, credits it issued to other identities, and trust scores. CR2SE has no global ledger and requires no consensus between ledgers.

**credit claim**
A secret, single-use bearer value created by a credit issuer to represent credits that do not yet have an identity owner. The holder may present it to the issuer and request assignment of those credits to an identity. A credit claim is not an identity private key. Use **credit claim**, not “claim key.”

**trust score** (short form: **trust**)
One identity's local, asymmetric evaluation of another identity. Trust is not global reputation or consensus and does not compel any identity to provide a service or recognize credits.

## Network roles

**initiator**
The node that opens a CR2SE network connection.

**acceptor**
The node that accepts a CR2SE network connection. Initiator and acceptor describe connection establishment only; after establishment, either peer may initiate operations.
