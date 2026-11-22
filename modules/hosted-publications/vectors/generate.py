#!/usr/bin/env python3
"""Independent generator for the Hosted Publications fixed vectors.

Uses only the `cryptography` package for Ed25519, X25519, HKDF-SHA-256 and ChaCha20-Poly1305,
plus a from-scratch HChaCha20 to build XChaCha20-Poly1305. It shares no code with any CR2SE
implementation. Run: python3 generate.py  (output is deterministic).
"""
import hashlib, struct
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization

M32 = 0xFFFFFFFF
def rotl(v, n): return ((v << n) & M32) | (v >> (32 - n))
def qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & M32; s[d] = rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & M32; s[b] = rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & M32; s[d] = rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & M32; s[b] = rotl(s[b] ^ s[c], 7)
def hchacha20(key, nonce16):
    s = list(struct.unpack('<4I', b'expand 32-byte k')) + list(struct.unpack('<8I', key)) + list(struct.unpack('<4I', nonce16))
    for _ in range(10):
        qr(s,0,4,8,12); qr(s,1,5,9,13); qr(s,2,6,10,14); qr(s,3,7,11,15)
        qr(s,0,5,10,15); qr(s,1,6,11,12); qr(s,2,7,8,13); qr(s,3,4,9,14)
    return struct.pack('<8I', *(s[0:4] + s[12:16]))
def xchacha_encrypt(key, nonce24, plaintext, aad):
    sub = hchacha20(key, nonce24[:16])
    return ChaCha20Poly1305(sub).encrypt(b'\0\0\0\0' + nonce24[16:], plaintext, aad)

# Self-check against the HChaCha20 test vector of draft-irtf-cfrg-xchacha, section 2.2.1.
assert hchacha20(bytes(range(32)), bytes.fromhex('000000090000004a0000000031415927')).hex() == (
    '82413b4227b27bfed30e42508a877d73a0f9e4d58a74a853c12ec41326d3ecdc')

sha = lambda b: hashlib.sha256(b).digest()
u32 = lambda v: struct.pack('>I', v)
u64 = lambda v: struct.pack('>Q', v)
lp = lambda s: u64(len(s.encode())) + s.encode()
def identity_id(pub): return sha(b'\x01\x01' + pub)
def raw_pub(k): return k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

PUBLISHER_SEED = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
READER_X_PRIV = bytes(range(0x40, 0x60))
EPHEMERAL_PRIV = bytes(range(0x80, 0xa0))
CONTENT_KEY = bytes(range(0xc0, 0xe0))
publisher = Ed25519PrivateKey.from_private_bytes(PUBLISHER_SEED)
publisher_pub = raw_pub(publisher); publisher_id = identity_id(publisher_pub)
reader_x = X25519PrivateKey.from_private_bytes(READER_X_PRIV); reader_x_pub = raw_pub(reader_x)
reader_id = identity_id(bytes(range(0x20, 0x40)))   # an identity ID used only as an audience entry

def signing_bytes(pid, kind, seq, at, vis, audience, content):
    return (b'CR2SE-PUBLICATION-V1' + pid + publisher_id + bytes([kind]) + u64(seq) + u64(at) + bytes([vis])
            + u32(len(audience)) + b''.join(audience) + u64(len(content)) + sha(content) + content)
def publication(label, pid, kind, seq, at, vis, audience, content):
    sb = signing_bytes(pid, kind, seq, at, vis, audience, content)
    sig = publisher.sign(sb)
    print(f'== {label}'); print('publicationId:', pid.hex()); print('contentSize:', len(content))
    print('contentHash:', sha(content).hex()); print('content:', content.hex())
    print('signingBytes:', sb.hex()); print('signingBytesSHA256:', sha(sb).hex()); print('publisherSignature:', sig.hex()); print()
    return sb, sig

print('publisherPublicKey:', publisher_pub.hex()); print('publisherId:', publisher_id.hex())
print('readerEncryptionPublicKey:', reader_x_pub.hex()); print('readerId (audience):', reader_id.hex()); print()

# V1: a public resource publication
res_id = bytes(range(0x00, 0x20)); res_content = b'<h1>hi</h1>\n'
publication('V1 public resource', res_id, 0x03, 0, 1000, 0x00, [], res_content)

# V2: a public page snapshot whose manifest references V1
manifest = (b'CR2SE-HOSTED-PAGE-MANIFEST-V1' + u32(1) + lp('/') + lp('text/html')
            + u64(len(res_content)) + sha(res_content) + res_id)
page_id = bytes(range(0x20, 0x40))
publication('V2 public page snapshot (manifest)', page_id, 0x01, 1, 1001, 0x00, [], manifest)

# V3: a restricted feed post for one reader
post_id = bytes(range(0x40, 0x60)); post_seq, post_at = 7, 1002
feed_message = (b'CR2SE-OPEN-SOCIAL-MESSAGE-V1' + post_id + publisher_id + u64(post_at) + lp('hi') + u32(0))
meta = (b'CR2SE-PUBLICATION-ENCRYPTION-METADATA-V1' + post_id + publisher_id + b'\x02' + u64(post_seq) + u64(post_at))
eph = X25519PrivateKey.from_private_bytes(EPHEMERAL_PRIV); eph_pub = raw_pub(eph)
content_nonce = bytes(range(0xe0, 0xf8)); wrap_nonce = bytes(range(0xa0, 0xb8))
ciphertext = xchacha_encrypt(CONTENT_KEY, content_nonce, feed_message, meta)
shared = eph.exchange(X25519PublicKey.from_public_bytes(reader_x_pub))
wrap_key = HKDF(hashes.SHA256(), 32, sha(meta), b'CR2SE-PUBLICATION-KEY-WRAP-V1').derive(shared)
wrapped = xchacha_encrypt(wrap_key, wrap_nonce, CONTENT_KEY, meta + reader_x_pub)
envelope = b'\x01' + eph_pub + content_nonce + u32(1) + reader_x_pub + wrap_nonce + wrapped + ciphertext
print('== V3 restricted feed post: encryption'); print('feedMessageBytes (plaintext):', feed_message.hex())
print('encryptionMetadataBytes:', meta.hex()); print('ephemeralPublicKey:', eph_pub.hex()); print('contentKey:', CONTENT_KEY.hex())
print('sharedSecret:', shared.hex()); print('wrapKey:', wrap_key.hex()); print('wrappedContentKey:', wrapped.hex())
print('contentCiphertext:', ciphertext.hex()); print('envelopeSize:', len(envelope)); print()
publication('V3 restricted feed post (envelope)', post_id, 0x02, post_seq, post_at, 0x01, [reader_id], envelope)
