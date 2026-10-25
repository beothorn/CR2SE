import motivation from '../../../AIMotivation.md?raw';

// Keep this byte-for-byte identical to the source, without any HTML wrapper.
export function GET() {
  return new Response(motivation, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
