# CR2SE

CR2SE is a peer-to-peer protocol in which identities exchange services for identity-issued credits. It is an alternative to funding infrastructure through advertising, monetary payments, or donations. It also supports decentralized networks that can be less exposed to scraping and attacks.  
Peers implementing CR2SE exchange services for credits. Credits are not a global currency but only relates to a single peer.  
Or in other words, on CR2SE each peer has their own currency.  

# CR2SE principles  

CR2SE principles are:  
- Trusted peers are easy to reach  
- Through shared resources and redundancy, data is persisted and accessed from any hardware, as long you have the keys  
- It is expensive for unknown, untrusted peers to reach peers, and impossibly expensive for reaching many untrusted peers  
- Untrusted is the default instance  
- Credits may be acquired in other ways (for example payments)  
- CR2SE can be a channel for any non real time service  

Domain terms have consistent meanings across the specifications and are defined in the [CR2SE Glossary](./Glossary.md).


# Components

- [Network](./Network.md) - Transport protocol  
- [NodeApi](./NodeApi.md) - Commands for boards, service definitions, invocation, and node control  
- [Identity](./Identity.md) - Identification  
- [Encryption](./Encryption.md) - Signing, encrypting, verifying  
- [Ledger](./Ledger.md) - Manage credit, debit and trust  
- [Board](./Board.md) - Compact service offerings, wanted services, payment terms, and metadata  
- [Services](./Services.md) - Separately retrievable service definitions, input/output schemas, types, and checks  
- [Glossary](./Glossary.md) - Common domain vocabulary  
- Storage - Resource Sharing Service  
- Computation - Resource Sharing Service  
- PublicFileSharing - Distributed hosting of files with public access  
- Messaging - Send encrypted messages to any peer, where a peer stores the message for you until recovery  
- OpenSocialMessaging - Peers delivery public messages, the client can gather all of them to show as a combined stream of messages 
- Page - Static HTML Page Hosting Service   
- Discovery - Find peers and services  
