/** Runtime ink treatment. The editable rig/geometry remains a single set of parts. */
export function applyGagooInk(model, T) {
  const bands = new T.DataTexture(new Uint8Array([70, 155, 235, 255]), 4, 1, T.RedFormat);
  bands.minFilter = bands.magFilter = T.NearestFilter;
  bands.generateMipmaps = false;
  bands.needsUpdate = true;
  const ink = new T.MeshBasicMaterial({color: 0x18232d, side: T.BackSide});
  ink.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>',
      '#include <begin_vertex>\ntransformed += normal * 0.032;');
  };
  ink.customProgramCacheKey = () => 'gagoo-ink-032-v1';
  const meshes = [], originals = [], outlines = [], tones = new Map();
  model.traverse(node => { if (node.isMesh && !node.material.transparent) meshes.push(node); });
  for (const node of meshes) {
    const material = node.material;
    originals.push([node, material, node.castShadow, node.receiveShadow]);
    if (!material.isMeshBasicMaterial) {
      if (!tones.has(material)) {
        const tone = new T.MeshToonMaterial({color: material.color, gradientMap: bands,
          side: material.side, emissive: material.emissive || 0x000000});
        // The pinned renderer supports this flag; Toon omits it from its constructor defaults.
        tone.flatShading = true;
        tones.set(material, tone);
      }
      node.material = tones.get(material);
    }
    node.castShadow = node.receiveShadow = true;
    // Keep the eyes and small painted details clean instead of stacking rings.
    if (/eye|pupil|status dot|display|patch|mouth|cuff|joint/.test(node.name)) continue;
    const outline = new T.Mesh(node.geometry, ink);
    outline.name = 'Gagoo ink silhouette';
    outline.userData.inkOutline = true;
    outline.raycast = () => {};
    node.add(outline);
    outlines.push(outline);
  }
  let disposed = false;
  return () => {
    if (disposed) return;
    disposed = true;
    for (const outline of outlines) outline.removeFromParent();
    for (const [node, material, cast, receive] of originals) {
      node.material = material; node.castShadow = cast; node.receiveShadow = receive;
    }
    for (const material of tones.values()) material.dispose();
    ink.dispose(); bands.dispose();
  };
}
