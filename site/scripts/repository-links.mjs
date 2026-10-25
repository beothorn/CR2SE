// Existing documents stay portable Markdown; site readers follow their links
// to the complete specification on GitHub.
export default function repositoryLinks() {
  return (tree, file) => {
    const source = String(file.history?.[0] || '').replaceAll('\\', '/');
    const filename = source.split('/').at(-1);
    if (!['README.md', 'Motivation.md'].includes(filename)) return;
    function visit(node) {
      if (node.type === 'link' && /^(\.\/)?[A-Za-z][^:]*\.md(?:#.*)?$/.test(node.url)) {
        node.url = `https://github.com/beothorn/CR2SE/blob/main/${node.url.replace(/^\.\//, '')}`;
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}
