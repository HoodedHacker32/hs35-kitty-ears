// ====================================================================== ASSEMBLY FILM
// Inlined into viewer_realistic_template.html by build_viewer_html.py --mode=assembly.
// Everything is a pure function of the film time t, so the same code drives the interactive page
// (real time, scrubbable) and the video render (frame by frame, with an offline-rendered soundtrack).
const FILM = (() => {
  const P = new URLSearchParams(location.search);
  const CAPTURE = P.has('capture');
  const BPM = 112, B = 60 / BPM, M0 = 4.2, bt = (n) => M0 + n * B;   // musical grid: events land on beats
  const DUR = 44;
  const TL = {
    printE: [bt(0.4), bt(20)], printC: [bt(0.8), bt(19)], printI: [bt(1.2), bt(12)], beep: bt(21),
    hop: { ear_L: bt(22), ear_R: bt(22.5), insert_L: bt(24), insert_R: bt(24.5) }, hopDur: 2.2 * B,
    away: [bt(27), bt(30)],
    L: { fly: [bt(32), bt(35)], ins: [bt(36), bt(38)], clip: [bt(39), bt(42)], snap: [bt(43), bt(46)] },
    R: { fly: [bt(47), bt(49.5)], ins: [bt(50), bt(52)], clip: [bt(53), bt(55)], snap: [bt(56), bt(58)] },
    tada: bt(60),
  };
  const CAPS = [
    [0.7, 3.9, 'title', 'Kitty Ears', 'for the Corsair HS35 v2'],
    [bt(0.5), bt(8), 'chip', 'Three plates, one filament each', 'No supports. No filament swaps.'],
    [bt(8.2), bt(13.5), 'chip', 'Plate 1 · the ears', 'Black PLA Matte, printed lying on their backs'],
    [bt(13.7), bt(17.4), 'chip', 'Plate 2 · the clips', 'Black PETG, printed standing up so they flex along the layers'],
    [bt(17.6), bt(21.4), 'chip', 'Plate 3 · the inner ears', 'Pink PLA, printed flat'],
    [bt(22), bt(31), 'chip', 'Everything onto one plate', 'Six parts, about 70 g of filament'],
    [bt(32), bt(38.6), 'chip', '1 · Press the inner ear in', 'It clicks in past three little tabs'],
    [bt(39), bt(42.6), 'chip', '2 · Slide the ear onto the clip', 'Rail into the open end of the groove, until it clicks'],
    [bt(43), bt(46.8), 'chip', '3 · Snap the clip onto the headband', 'Centred over the band, then press'],
    [bt(47), bt(58.4), 'chip', 'Same again, mirrored', 'Click · click · snap'],
    [bt(60), DUR, 'title end', 'Clickety-clack. No glue.', 'Pull an ear firmly outward to take it off'],
  ];

  // ---------------------------------------------------------------- helpers
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const win = (t, [a, b]) => clamp01((t - a) / (b - a));
  const ease = (k) => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
  const easeIn = (k) => k * k * k;
  const smooth = (k) => k * k * (3 - 2 * k);
  const M4 = (a) => new THREE.Matrix4().fromArray(a);
  const T4 = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
  const dec = (m) => { const p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3(); m.decompose(p, q, s); return { p, q }; };
  const ONE = new THREE.Vector3(1, 1, 1);
  function blend(a, b, k, arc = 0) {   // rigid pose a -> b, with an optional upward arc (world z)
    const p = a.p.clone().lerp(b.p, k); p.z += arc * Math.sin(Math.PI * k);
    return { p, q: a.q.clone().slerp(b.q, k) };
  }
  const mat = (ps) => new THREE.Matrix4().compose(ps.p, ps.q, ONE);

  // ---------------------------------------------------------------- stage: three print beds in front of the headset
  const PLATE_TOP = -340, BED_Y = -420;
  const BEDS = { E: -310, C: 0, I: 310 };
  key.position.set(260, 520, 380); scene.add(key.target);
  renderer.toneMappingExposure = 1.12;
  const filmFill = new THREE.HemisphereLight(0xf4f0ff, 0x302a2e, 0.55); scene.add(filmFill);
  const spot = new THREE.SpotLight(0xffe9f2, 2.2, 0, 0.5, 0.8, 0); spot.position.set(-300, 700, 300); scene.add(spot); scene.add(spot.target);
  Object.assign(key.shadow.camera, { left: -300, right: 300, top: 300, bottom: -300 }); key.shadow.camera.updateProjectionMatrix();
  const pei = (() => {   // textured PEI sheet: warm gold with a fine speckle
    const S = 512, [c, x] = canvas2d(S); const R = rng(5);
    x.fillStyle = '#7a6230'; x.fillRect(0, 0, S, S);
    for (let i = 0; i < 26000; i++) { const v = R(); x.fillStyle = v > 0.5 ? 'rgba(255,226,160,0.18)' : 'rgba(40,28,10,0.22)'; x.fillRect(R() * S, R() * S, 1 + R() * 1.6, 1 + R() * 1.6); }
    return c;
  })();
  const peiMap = tex(pei, true); peiMap.repeat.set(3, 3);
  const peiN = normalFromHeight(grain(21, 512), 2.2); peiN.repeat.set(6, 6);
  const plateMat = new THREE.MeshPhysicalMaterial({ map: peiMap, roughness: 0.62, metalness: 0.35, normalMap: peiN, normalScale: new THREE.Vector2(0.6, 0.6), clearcoat: 0.2, clearcoatRoughness: 0.5 });
  const alu = new THREE.MeshPhysicalMaterial({ color: 0x5a5e66, metalness: 0.9, roughness: 0.32 });
  const shellMat = new THREE.MeshPhysicalMaterial({ color: 0x16171a, roughness: 0.45, clearcoat: 0.4, clearcoatRoughness: 0.25 });
  const brass = new THREE.MeshPhysicalMaterial({ color: 0xc9a25a, metalness: 1, roughness: 0.25 });
  const led = new THREE.MeshBasicMaterial({ color: new THREE.Color('#f2a7c3').multiplyScalar(2.2) });
  const beds = {};
  for (const [id, x] of Object.entries(BEDS)) {
    const g = new THREE.Group(); g.position.set(x, BED_Y, 0); world.add(g);
    const carriage = mesh(new THREE.BoxGeometry(296, 296, 7), alu, g); carriage.position.z = PLATE_TOP - 1.2 - 3.5;
    const plate = mesh(new THREE.BoxGeometry(256, 256, 1.2), plateMat, g); plate.position.z = PLATE_TOP - 0.6;
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) { const f = mesh(new THREE.CylinderGeometry(6, 7, 6, 24), alu, g); f.rotation.x = Math.PI / 2; f.position.set(sx * 130, sy * 130, PLATE_TOP - 9); }
    // toolhead (origin = nozzle tip) on a gantry
    const head = new THREE.Group(); g.add(head);
    const noz = mesh(new THREE.ConeGeometry(2.6, 5, 24), brass, head); noz.rotation.x = -Math.PI / 2; noz.position.z = 2.5;
    const blk = mesh(new THREE.BoxGeometry(17, 17, 9), alu, head); blk.position.z = 9.5;
    const body = mesh(new RoundedBoxGeometry(48, 44, 46, 4, 6), shellMat, head); body.position.z = 37;
    const strip = mesh(new THREE.BoxGeometry(30, 0.8, 2.2), led, head); strip.position.set(0, -22.2, 30); strip.castShadow = false;
    const gantry = mesh(new THREE.BoxGeometry(330, 14, 12), alu, g);
    const posts = [-1, 1].map(sx => { const p = mesh(new THREE.BoxGeometry(9, 9, 1), alu, g); p.position.x = sx * 165; return p; });
    beds[id] = { g, head, gantry, posts, x };
  }
  const rings = [];
  for (let i = 0; i < 6; i++) {
    const r = new THREE.Mesh(new THREE.RingGeometry(0.82, 1, 96), new THREE.MeshBasicMaterial({ color: 0xffd2e4, transparent: true, opacity: 0, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
    r.renderOrder = 10; scene.add(r); rings.push(r);
  }

  // ---------------------------------------------------------------- parts: plate poses, work poses, final poses
  const PART = {
    ear_L:    { bed: 'E', off: [36, 0],   gather: [64, 58],   mat: 'earPLA' },
    ear_R:    { bed: 'E', off: [-36, 0],  gather: [-64, 58],  mat: 'earPLA' },
    clip_L:   { bed: 'C', off: [14, 0],   gather: [16, -6],   mat: 'petg' },
    clip_R:   { bed: 'C', off: [-14, 0],  gather: [-16, -6],  mat: 'petg' },
    insert_L: { bed: 'I', off: [22, 0],   gather: [64, -62],  mat: 'pla' },
    insert_R: { bed: 'I', off: [-22, 0],  gather: [-64, -62], mat: 'pla' },
  };
  const ML = M4(META.place.L), MR = M4(META.place.R);
  const HOV = 78;
  let parts = null, ready = false;
  function attach(p) {
    parts = p;
    const fin = {}; for (const n of Object.keys(PART)) fin[n] = M4(META.parts[n].final);
    // the clip is symmetric in x, so the right clip is the same print turned around (no mirror matrix)
    fin.clip_R = MR.clone().multiply(ML.clone().invert()).multiply(fin.clip_L);
    for (const [n, d] of Object.entries(PART)) {
      const m = parts[n]; m.matrixAutoUpdate = false;
      d.mesh = m; d.h = META.parts[n].h; d.ext = META.parts[n].ext;
      d.F = dec(fin[n]);
      const side = n.endsWith('_L') ? 'L' : 'R', Mp = side === 'L' ? ML : MR, s = side === 'L' ? 1 : -1;
      const local = (x, y, z) => Mp.clone().multiply(T4(x, y, z)).multiply(Mp.clone().invert()).multiply(fin[n]);
      d.W = dec(local(0, 0, HOV));                                   // hovering above its spot on the band
      if (n.startsWith('insert')) d.A = dec(local(0, -42, HOV));       // in front of the ear, ready to press in
      if (n.startsWith('clip')) d.A = dec(local(-s * 62, 0, HOV));     // beside the ear, ready to slide in
      const bx = BEDS[d.bed] + d.off[0], by = BED_Y + d.off[1];
      d.P = { p: V(bx, by, PLATE_TOP), q: new THREE.Quaternion() };
      d.G = { p: V(BEDS.C + d.gather[0], BED_Y + d.gather[1], PLATE_TOP), q: new THREE.Quaternion() };
      d.side = side;
      const bb = m.geometry.boundingBox || (m.geometry.computeBoundingBox(), m.geometry.boundingBox);
      d.c = bb.getCenter(new THREE.Vector3());
    }
    for (const id of Object.keys(BEDS)) beds[id].parts = Object.entries(PART).filter(([, d]) => d.bed === id).map(([, d]) => d);
    for (const k of ['earPLA', 'petg', 'pla']) M[k].side = THREE.DoubleSide;
    ready = true; seek(P.has('t') ? +P.get('t') : 0);
    if (!CAPTURE) ui();
  }

  // ---------------------------------------------------------------- the timeline
  const prog = { E: (t) => win(t, TL.printE), C: (t) => win(t, TL.printC), I: (t) => win(t, TL.printI) };
  const hMax = { E: () => PART.ear_L.h, C: () => PART.clip_L.h, I: () => PART.insert_L.h };
  const matOf = { E: 'earPLA', C: 'petg', I: 'pla' };
  function partPose(n, d, t) {
    const S = TL[d.side], kind = n.split('_')[0];
    // 1. on its print bed (with a little "pop" when the plate is flexed)
    let ps = d.P;
    const pe = prog[d.bed](t);
    if (pe >= 1) { const k = clamp01((t - TL.beep - 0.15) / 0.25); ps = { p: d.P.p.clone().add(V(0, 0, 3 * Math.sin(Math.PI * k))), q: d.P.q }; }
    // 2. hop onto the one plate
    const th = TL.hop[n];
    if (th !== undefined && t >= th) ps = blend(d.P, d.G, ease(clamp01((t - th) / TL.hopDur)), 150);
    if (th === undefined && t >= TL.hop.ear_L) ps = blend(d.P, d.G, ease(clamp01((t - TL.hop.ear_L - B) / (1.5 * B))), 18);
    // 3. fly up to the headset
    if (t >= S.fly[0]) {
      const lag = { ear: 0, insert: 0.12, clip: 0.24 }[kind];
      const k = ease(clamp01((t - S.fly[0] - lag) / (S.fly[1] - S.fly[0] - 0.24)));
      ps = blend(d.G, kind === 'ear' ? d.W : d.A, k, 120);
    }
    // 4. insert presses in, clip slides in (ease-in = it accelerates into the click)
    if (kind === 'insert' && t >= S.ins[0]) ps = blend(d.A, d.W, easeIn(win(t, S.ins)));
    if (kind === 'clip' && t >= S.clip[0]) ps = blend(d.A, d.W, easeIn(win(t, S.clip)));
    // 5. the finished ear goes down onto the headband
    if (t >= S.snap[0]) ps = blend(d.W, d.F, easeIn(win(t, S.snap)));
    // tiny recoil after each click
    const bump = (te, amp) => { const u = t - te; return u > 0 && u < 0.35 ? amp * Math.sin(u * 40) * Math.exp(-u * 14) : 0; };
    const Mp = d.side === 'L' ? ML : MR;
    const nrm = V(Mp.elements[8], Mp.elements[9], Mp.elements[10]);
    const r = bump(S.ins[1], 0.8) + bump(S.clip[1], 0.8) + bump(S.snap[1], 1.6);
    if (r && t >= S.ins[1]) ps = { p: ps.p.clone().addScaledVector(nrm, r), q: ps.q };
    return ps;
  }
  function headPose(bed, t) {
    const p = prog[bed](t), ps = beds[bed].parts, hz = hMax[bed]();
    if (p <= 0 || p >= 1) {   // parked high at the back
      return V(0, 110, Math.max(70, hz + 50));
    }
    const slot = t * 2.4, i = Math.floor(slot), f = slot - i;
    const at = (j, tt) => { const d = ps[((j % ps.length) + ps.length) % ps.length]; const e = d.ext; return V(d.off[0] + e[0] * 0.4 * Math.sin(tt * 11.3 + j), d.off[1] + e[1] * 0.4 * Math.sin(tt * 7.9 + 2 * j), 0); };
    const a = at(i - 1, t), b = at(i, t), q = a.lerp(b, smooth(clamp01(f / 0.3)));
    q.z = p * hz + 0.2 + (f < 0.3 ? 1.2 * Math.sin(Math.PI * f / 0.3) : 0);   // z-hop on travel
    return q;
  }

  // ---------------------------------------------------------------- camera (authored coordinates: z up, front = -y)
  const LO = new THREE.Vector3().setFromMatrixPosition(ML), RO = new THREE.Vector3().setFromMatrixPosition(MR);
  const nL = V(ML.elements[8], ML.elements[9], ML.elements[10]), nR = V(MR.elements[8], MR.elements[9], MR.elements[10]);
  const hovL = LO.clone().addScaledVector(nL, HOV + 22), hovR = RO.clone().addScaledVector(nR, HOV + 22);
  const KEYS = [
    [0.0, [-60, -1180, -150], [0, -420, -330]],
    [3.8, [-170, -1000, -170], [-40, -420, -335]],
    [bt(0.5), [0, -900, -110], [0, -420, -330]],
    [bt(7.5), [-90, -840, -150], [-60, -420, -330]],
    [bt(8.6), [-200, -560, -240], [-310, -415, -322]],
    [bt(13.2), [-250, -545, -255], [-300, -420, -318]],
    [bt(14.0), [80, -540, -250], [0, -420, -316]],
    [bt(17.2), [40, -560, -262], [0, -420, -318]],
    [bt(17.8), [400, -570, -270], [310, -420, -336]],
    [bt(21.4), [370, -590, -255], [300, -420, -336]],
    [bt(22.4), [0, -760, -60], [0, -440, -335]],
    [bt(29.5), [-60, -700, -70], [0, -430, -335]],
    [bt(32.2), [260, -560, 70], [70, -140, -60]],
    [bt(35.4), [hovL.x + 140, -190, hovL.z + 40], [hovL.x, 0, hovL.z]],
    [bt(38.8), [hovL.x + 120, -150, hovL.z + 30], [hovL.x, 0, hovL.z - 5]],
    [bt(42.6), [hovL.x + 150, -210, hovL.z + 10], [hovL.x - 5, 0, hovL.z - 20]],
    [bt(46.5), [LO.x + 230, -300, LO.z + 70], [LO.x - 10, 0, LO.z]],
    [bt(48.0), [hovR.x - 180, -260, hovR.z + 40], [hovR.x, 0, hovR.z - 10]],
    [bt(55.5), [hovR.x - 160, -230, hovR.z + 20], [hovR.x, 0, hovR.z - 25]],
    [bt(58.2), [RO.x - 260, -330, RO.z + 60], [RO.x + 20, 0, RO.z - 10]],
  ];
  const HERO = bt(58.2);
  function camAt(t) {
    let p, q;
    if (t >= HERO) {   // slow hero orbit around the finished headset
      const k = (t - HERO) / (DUR - HERO), a = -2.2 + 1.7 * smooth(Math.min(1, k * 1.15)), r = 760 - 80 * smooth(k);
      const tg = V(0, 0, -95);
      p = V(tg.x + r * Math.cos(a), tg.y + r * Math.sin(a), 70 - 40 * k); q = tg;
      const k0 = clamp01((t - HERO) / 1.6);
      if (k0 < 1) { const [pa, qa] = camKeys(HERO); p = pa.lerp(p, ease(k0)); q = qa.lerp(q, ease(k0)); }
      return [p, q];
    }
    return camKeys(t);
  }
  function camKeys(t) {
    let i = 0; while (i < KEYS.length - 1 && KEYS[i + 1][0] <= t) i++;
    const a = KEYS[i], b = KEYS[Math.min(i + 1, KEYS.length - 1)];
    const k = b[0] > a[0] ? ease(clamp01((t - a[0]) / (b[0] - a[0]))) : 0;
    return [V(...a[1]).lerp(V(...b[1]), k), V(...a[2]).lerp(V(...b[2]), k)];
  }

  // ---------------------------------------------------------------- apply time t to the whole scene
  let T = 0;
  const clicks = [];
  for (const s of ['L', 'R']) { const S = TL[s]; clicks.push([S.ins[1], 'insert_' + s, 60], [S.clip[1], 'clip_' + s, 70], [S.snap[1], 'clip_' + s, 120]); }
  function apply(t) {
    T = t;
    for (const id of Object.keys(BEDS)) {
      const p = prog[id](t), m = M[matOf[id]];
      m.userData.u.uCut.value = p <= 0 ? -1 : p >= 1 ? 1e6 : p * hMax[id]();
      m.userData.u.uHot.value = p > 0 && p < 1 ? 1 : 0;
      const b = beds[id], hp = headPose(id, t);
      // park move after the print: glide up and back
      const done = p >= 1 ? clamp01((t - [TL.printE, TL.printC, TL.printI][['E', 'C', 'I'].indexOf(id)][1]) / 0.7) : 0;
      const pos = p >= 1 ? V(0, 0, hMax[id]() + 0.2).lerp(V(0, 110, Math.max(70, hMax[id]() + 50)), smooth(done)) : hp;
      b.head.position.set(pos.x, pos.y, PLATE_TOP + pos.z);
      b.gantry.position.set(0, pos.y, PLATE_TOP + pos.z + 52);
      for (const ps of b.posts) { const h = pos.z + 52 + 12; ps.scale.z = h; ps.position.set(ps.position.x, pos.y, PLATE_TOP + h / 2 - 12); }
      // the two side beds slide away once the parts are on the middle one
      const aw = id === 'C' ? ease(win(t, [TL.R.fly[1], TL.R.fly[1] + 2.5])) : ease(win(t, TL.away));
      b.g.position.set(b.x + (Math.sign(b.x) || 0) * 260 * aw, BED_Y - (id === 'C' ? 500 : -120) * aw, -60 * aw * aw);
      b.g.visible = aw < 0.999;
    }
    for (const [n, d] of Object.entries(PART)) {
      const ps = partPose(n, d, t);
      d.mesh.matrix.copy(mat(ps)); d.mesh.matrixWorldNeedsUpdate = true;
      const p = prog[d.bed](t);
      d.mesh.visible = p > 0;
      d.mesh.castShadow = p >= 1;
      d.mesh.layers.set(p > 0 && p < 1 ? 1 : 0);   // half-printed parts are left out of the AO pass
    }
    // camera + click shake
    let [p, q] = camAt(t);
    let shake = 0;
    for (const [te, , amp] of clicks) { const u = t - te; if (u > 0 && u < 0.5) shake += amp * 0.004 * Math.exp(-u * 10); }
    if (shake) p = p.clone().add(V(Math.sin(t * 91) * shake * 10, 0, Math.cos(t * 77) * shake * 10));
    if (follow) { cam.position.copy(W2V(p.x, p.y, p.z)); ctl.target.copy(W2V(q.x, q.y, q.z)); cam.lookAt(ctl.target); }
    // shadows follow the action
    const tg = W2V(q.x, q.y, q.z); spot.target.position.copy(tg); spot.target.updateMatrixWorld(); spot.position.copy(tg).add(V(-320, 620, 340)); key.target.position.copy(tg); key.position.copy(tg).add(V(260, 520, 380)); key.target.updateMatrixWorld();
    // click rings
    let ri = 0;
    for (const [te, n, amp] of clicks) {
      const u = t - te; if (u < 0 || u > 0.7 || ri >= rings.length) continue;
      const r = rings[ri++], d = PART[n];
      const c = d.c.clone().applyMatrix4(d.mesh.matrix); world.localToWorld(c);
      r.position.copy(c); r.quaternion.copy(cam.quaternion);
      const s = 8 + amp * 0.5 * smooth(clamp01(u / 0.7)); r.scale.set(s, s, s);
      r.material.opacity = 0.9 * (1 - clamp01(u / 0.7));
    }
    for (; ri < rings.length; ri++) rings[ri].material.opacity = 0;
    caption(t);
  }

  // ---------------------------------------------------------------- captions
  const capEl = document.createElement('div'); capEl.id = 'cap'; document.body.appendChild(capEl);
  const style = document.createElement('style'); style.textContent = `
    #cap { position:fixed; inset:0; pointer-events:none; font-family: "Segoe UI Variable Display","Segoe UI",system-ui,sans-serif; }
    #cap .title { position:absolute; left:0; right:0; top:38%; text-align:center; color:#fff; text-shadow:0 4px 30px #000c; }
    #cap .title.end { top:auto; bottom:9%; }
    #cap .title b { display:block; font-size:clamp(34px,7vw,88px); font-weight:800; letter-spacing:-.02em; }
    #cap .title b em { font-style:normal; color:#f2a7c3; }
    #cap .title span { display:block; margin-top:6px; font-size:clamp(14px,2.2vw,26px); color:#e6e3df; font-weight:500; }
    #cap .chip { position:absolute; left:clamp(16px,5vw,64px); bottom:clamp(96px,14vh,150px); max-width:min(560px,80vw); color:#fff;
                 padding:14px 20px 14px 18px; border-radius:16px; background:#151518cc; border:1px solid #ffffff1c; backdrop-filter:blur(8px);
                 box-shadow:0 10px 40px #0008; border-left:4px solid #f2a7c3; }
    #cap .chip b { display:block; font-size:clamp(17px,2.2vw,26px); font-weight:700; }
    #cap .chip span { display:block; margin-top:3px; font-size:clamp(13px,1.5vw,17px); color:#cfcbc6; }
    body.capture #cap .chip { bottom:70px; }`;
  document.head.appendChild(style);
  if (CAPTURE) document.body.classList.add('capture');
  let capKey = '';
  function caption(t) {
    const c = CAPS.find(([a, b]) => t >= a && t < b);
    const k = c ? c[3] : '';
    if (k !== capKey) {
      capKey = k;
      capEl.innerHTML = c ? `<div class="${c[2]}"><b>${c[3].replace('Kitty', '<em>Kitty</em>').replace('No glue.', '<em>No glue.</em>')}</b><span>${c[4]}</span></div>` : '';
    }
    const el = capEl.firstChild; if (!el) return;
    const a = clamp01((t - c[0]) / 0.35), b = clamp01((c[1] - t) / 0.35), o = Math.min(a, b);
    el.style.opacity = o; el.style.transform = `translateY(${(1 - smooth(a)) * 14}px)`;
  }

  // ---------------------------------------------------------------- rendering
  const aoCam = cam.clone();
  gtao.camera = aoCam;
  cam.layers.enable(1);
  function render() {
    world.updateMatrixWorld(true);
    cam.near = 0.5; cam.updateProjectionMatrix();
    aoCam.copy(cam); aoCam.layers.set(0); aoCam.updateMatrixWorld(); aoCam.updateProjectionMatrix();
    if (useAO || CAPTURE) composer.render(); else renderer.render(scene, cam);
  }
  function seek(t) { apply(Math.max(0, Math.min(DUR, t))); render(); }

  // ---------------------------------------------------------------- sound: synthesised, rendered offline so it is sample-accurate
  async function score() {
    const SR = 48000, N = Math.ceil(DUR * SR);
    const ctx = new OfflineAudioContext(2, N, SR);
    const R = rng(1234);
    const master = ctx.createGain(); master.gain.value = 0.85;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.knee.value = 8; comp.ratio.value = 3.5; comp.attack.value = 0.003; comp.release.value = 0.2;
    master.connect(comp).connect(ctx.destination);
    const rev = ctx.createConvolver();
    { const L = 2.6 * SR, ir = ctx.createBuffer(2, L, SR);
      for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < L; i++) d[i] = (R() * 2 - 1) * Math.pow(1 - i / L, 3.2) * (i < 0.004 * SR ? i / (0.004 * SR) : 1); }
      rev.buffer = ir; }
    const revOut = ctx.createGain(); revOut.gain.value = 0.32; rev.connect(revOut).connect(master);
    const musicF = ctx.createBiquadFilter(); musicF.type = 'lowpass'; musicF.Q.value = 0.9;
    const music = ctx.createGain(); musicF.connect(music).connect(master);
    const sfx = ctx.createGain(); sfx.gain.value = 1; sfx.connect(master);
    const noise = ctx.createBuffer(1, 2 * SR, SR); { const d = noise.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = R() * 2 - 1; }
    const send = (node, amt) => { const g = ctx.createGain(); g.gain.value = amt; node.connect(g).connect(rev); };
    const env = (g, t, a, peak, d, sustain = 0.0001) => { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(Math.max(sustain, 0.0001), t + a + d); };
    const osc = (type, f, t, dur, out) => { const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(f, t); o.connect(out); o.start(t); o.stop(t + dur + 0.05); return o; };
    const nsrc = (t, dur, out, rate = 1) => { const s = ctx.createBufferSource(); s.buffer = noise; s.loop = true; s.playbackRate.value = rate; s.connect(out); s.start(t, R() * 1.5); s.stop(t + dur + 0.05); return s; };
    const filt = (type, f, q, out) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; b.connect(out); return b; };
    const pan = (p, out) => { const s = ctx.createStereoPanner(); s.pan.value = p; s.connect(out); return s; };
    const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);

    // ---- instruments
    const kick = (t, v = 0.9) => { const g = ctx.createGain(); g.connect(music); env(g, t, 0.002, v, 0.32); const o = osc('sine', 150, t, 0.4, g); o.frequency.exponentialRampToValueAtTime(42, t + 0.13); };
    const hat = (t, v = 0.12, open = false) => { const g = ctx.createGain(); g.connect(pan(0.25, music)); env(g, t, 0.001, v, open ? 0.18 : 0.035); nsrc(t, 0.25, filt('highpass', 7500, 0.7, g)); };
    const clap = (t, v = 0.28) => { const g = ctx.createGain(); g.connect(music); send(g, 0.4); const bp = filt('bandpass', 1500, 0.8, g);
      g.gain.setValueAtTime(0.0001, t); for (const o of [0, 0.011, 0.022]) { g.gain.setValueAtTime(v, t + o); g.gain.exponentialRampToValueAtTime(v * 0.3, t + o + 0.009); } g.gain.exponentialRampToValueAtTime(0.0001, t + 0.16); nsrc(t, 0.2, bp); };
    const bass = (t, m, d, v = 0.32) => { const g = ctx.createGain(); g.connect(music); env(g, t, 0.006, v, d); const lp = filt('lowpass', 900, 2, g);
      lp.frequency.setValueAtTime(1400, t); lp.frequency.exponentialRampToValueAtTime(260, t + d); osc('triangle', hz(m), t, d, lp); osc('sine', hz(m - 12), t, d, g); };
    const pluck = (t, m, v = 0.12, p = 0, d = 0.32) => { const g = ctx.createGain(); g.connect(pan(p, music)); send(g, 0.25); env(g, t, 0.003, v, d);
      osc('sine', hz(m), t, d, g); const g2 = ctx.createGain(); g2.connect(g); env(g2, t, 0.001, 0.5, 0.06); osc('sine', hz(m) * 4, t, 0.1, g2); };
    const marimba = (t, m, v = 0.2, d = 0.5) => { const g = ctx.createGain(); g.connect(pan(-0.15, music)); send(g, 0.3); env(g, t, 0.002, v, d);
      osc('sine', hz(m), t, d, g); const g3 = ctx.createGain(); g3.connect(g); env(g3, t, 0.001, 0.35, 0.08); osc('sine', hz(m) * 3.93, t, 0.12, g3); };
    const chime = (t, m, v = 0.12, p = 0, d = 2.2) => { const g = ctx.createGain(); g.connect(pan(p, sfx)); send(g, 0.8); env(g, t, 0.002, v, d);
      for (const [r, a] of [[1, 1], [2.76, 0.4], [5.4, 0.18]]) { const gg = ctx.createGain(); gg.gain.value = a; gg.connect(g); osc('sine', hz(m) * r, t, d, gg); } };
    const pad = (t0, t1, notes, v = 0.06) => { const g = ctx.createGain(); g.connect(music); send(g, 0.6);
      g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(v, t0 + 1.2); g.gain.setValueAtTime(v, t1 - 1.2); g.gain.exponentialRampToValueAtTime(0.0001, t1);
      const lp = filt('lowpass', 1100, 0.5, g); for (const m of notes) for (const det of [-7, 7]) { const o = osc('sawtooth', hz(m), t0, t1 - t0, lp); o.detune.value = det; } };
    const riser = (t0, t1, v = 0.18) => { const g = ctx.createGain(); g.connect(sfx); send(g, 0.5); g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(v, t1);
      g.gain.exponentialRampToValueAtTime(0.0001, t1 + 0.08); const bp = filt('bandpass', 300, 1.4, g); bp.frequency.setValueAtTime(300, t0); bp.frequency.exponentialRampToValueAtTime(7000, t1); nsrc(t0, t1 - t0 + 0.1, bp); };
    const boom = (t, v = 0.8) => { const g = ctx.createGain(); g.connect(sfx); send(g, 0.4); env(g, t, 0.004, v, 1.6); const o = osc('sine', 90, t, 1.7, g); o.frequency.exponentialRampToValueAtTime(38, t + 0.9);
      const g2 = ctx.createGain(); g2.connect(sfx); env(g2, t, 0.002, 0.3, 0.5); nsrc(t, 0.6, filt('lowpass', 260, 0.7, g2)); };
    const whoosh = (t, d, v = 0.22, p0 = -0.6, p1 = 0.6) => { const g = ctx.createGain(); const sp = ctx.createStereoPanner(); g.connect(sp).connect(sfx); send(g, 0.3);
      sp.pan.setValueAtTime(p0, t); sp.pan.linearRampToValueAtTime(p1, t + d);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(v, t + d * 0.55); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
      const bp = filt('bandpass', 400, 1.1, g); bp.frequency.setValueAtTime(350, t); bp.frequency.exponentialRampToValueAtTime(2600, t + d * 0.55); bp.frequency.exponentialRampToValueAtTime(500, t + d); nsrc(t, d, bp); };
    const pop = (t, v = 0.35, p = 0) => { const g = ctx.createGain(); g.connect(pan(p, sfx)); env(g, t, 0.002, v, 0.11); const o = osc('sine', 950, t, 0.14, g); o.frequency.exponentialRampToValueAtTime(230, t + 0.08); };
    const click = (t, v = 1, pitch = 1, p = 0) => {
      const out = pan(p, sfx);
      const g1 = ctx.createGain(); g1.connect(out); env(g1, t, 0.0006, 0.55 * v, 0.012); nsrc(t, 0.03, filt('highpass', 3200, 0.7, g1));
      const g2 = ctx.createGain(); g2.connect(out); send(g2, 0.12); env(g2, t, 0.0008, 0.32 * v, 0.03); osc('sine', 2900 * pitch, t, 0.05, g2);
      const g3 = ctx.createGain(); g3.connect(out); env(g3, t, 0.001, 0.6 * v, 0.045); const o = osc('sine', 260 * pitch, t, 0.06, g3); o.frequency.exponentialRampToValueAtTime(90, t + 0.04);
    };
    const duck = (t, depth = 0.45) => { music.gain.setValueAtTime(1, t - 0.005); music.gain.linearRampToValueAtTime(depth, t + 0.01); music.gain.linearRampToValueAtTime(1, t + 0.3); };
    const sparkle = (t, root = 84, v = 0.1) => { [0, 4, 7, 12].forEach((iv, i) => chime(t + 0.045 * i, root + iv, v * (1 - i * 0.12), -0.4 + i * 0.27, 1.6)); };
    const beep = (t, m, d = 0.12, v = 0.08) => { const g = ctx.createGain(); g.connect(sfx); env(g, t, 0.004, v, d); osc('square', hz(m), t, d, filt('lowpass', 2400, 0.5, g)); };

    // ---- arrangement
    const CH = [[48, [60, 64, 67]], [43, [59, 62, 67]], [45, [60, 64, 69]], [41, [60, 65, 69]]];   // C  G  Am  F
    const MEL = [[[0, 76], [1, 79], [1.5, 84], [2.5, 79], [3, 76]], [[0, 74], [1, 79], [1.5, 83], [2.5, 86], [3, 83]],
                 [[0, 72], [1, 76], [1.5, 81], [2.5, 84], [3, 81]], [[0, 81], [1, 84], [1.5, 77], [2.5, 81], [3.5, 79]]];
    // intro: pad, shimmer, title ding, riser into the downbeat
    pad(0.1, M0 + 0.6, [60, 64, 67, 71], 0.05);
    for (let i = 0; i < 14; i++) chime(0.5 + i * 0.21 + R() * 0.05, 84 + [0, 4, 7, 11, 12, 16][Math.floor(R() * 6)], 0.035, R() * 1.6 - 0.8, 1.4);
    chime(0.8, 72, 0.12, -0.2, 3); chime(0.8, 76, 0.1, 0.2, 3); chime(0.8, 79, 0.09, 0, 3);
    riser(M0 - 1.3, M0, 0.16); boom(M0, 0.75);
    // filtered groove while printing, opens up when the parts come off the plates
    musicF.frequency.setValueAtTime(900, 0); musicF.frequency.setValueAtTime(900, bt(20)); musicF.frequency.exponentialRampToValueAtTime(14000, bt(22));
    riser(bt(19.5), bt(22), 0.12);
    for (let beat = 0; beat < 58; beat++) {
      const t = bt(beat), bar = Math.floor(beat / 4), inBar = beat % 4, [root, tri] = CH[bar % 4];
      const full = beat >= 22, drop = beat >= 56;
      if (!drop && (inBar === 0 || inBar === 2 || (full && inBar === 3 && bar % 2))) kick(t, full ? 0.9 : 0.6);
      if (full && !drop && (inBar === 1 || inBar === 3)) clap(t, 0.24);
      if (!drop) { hat(t + B / 2, full ? 0.11 : 0.07); if (full) hat(t + B / 4, 0.035); if (full) hat(t + 3 * B / 4, 0.035); }
      if (!drop) { bass(t, root, B * 0.42, full ? 0.3 : 0.22); bass(t + B / 2, root + (inBar === 3 ? 7 : 12), B * 0.3, full ? 0.22 : 0.15); }
      for (let k = 0; k < 2; k++) pluck(t + k * B / 2, tri[(inBar * 2 + k) % 3] + 12, full ? 0.07 : 0.05, k ? 0.35 : -0.35);
      if (beat >= 28 && !drop && inBar === 0) for (const [o, m] of MEL[bar % 4]) marimba(t + o * B, m, 0.16, 0.45);
    }
    // printers: stepper "singing", fans, and the done beep
    for (const [id, x] of [['E', -0.6], ['C', 0], ['I', 0.6]]) {
      const [a, b] = id === 'E' ? TL.printE : id === 'C' ? TL.printC : TL.printI;
      const g = ctx.createGain(); g.gain.value = 0.022; const bp = filt('bandpass', 1300, 0.9, g); g.connect(pan(x, sfx));
      for (let t = a; t < b; t += 0.085) { const og = ctx.createGain(); og.connect(bp); env(og, t, 0.004, 1, 0.08, 0.3); osc('square', [392, 440, 523, 587, 659, 784][Math.floor(R() * 6)] * (id === 'C' ? 0.75 : 1), t, 0.09, og); }
      const fan = ctx.createGain(); fan.gain.setValueAtTime(0.0001, a - 0.3); fan.gain.exponentialRampToValueAtTime(0.02, a); fan.gain.setValueAtTime(0.02, b); fan.gain.exponentialRampToValueAtTime(0.0001, b + 0.6);
      fan.connect(pan(x, sfx)); nsrc(a - 0.3, b - a + 1, filt('lowpass', 520, 0.6, fan));
      beep(b + 0.02, 84, 0.08); beep(b + 0.14, 91, 0.12);
    }
    beep(TL.beep, 88, 0.1); beep(TL.beep + 0.13, 91, 0.1); beep(TL.beep + 0.26, 96, 0.18);
    // parts come off the plates and hop over
    for (const [n, t] of Object.entries(TL.hop)) { pop(t, 0.32, n.endsWith('L') ? 0.4 : -0.4); whoosh(t + 0.05, TL.hopDur, 0.12, -0.5, 0.5); }
    pop(TL.hop.ear_L + B, 0.2, 0.2); pop(TL.hop.ear_L + B + 0.06, 0.2, -0.2);
    whoosh(TL.away[0], TL.away[1] - TL.away[0], 0.14, -0.9, 0.9);
    // assembly: whooshes, clicks, snaps
    for (const s of ['L', 'R']) {
      const S = TL[s], p = s === 'L' ? 0.35 : -0.35;
      whoosh(S.fly[0], S.fly[1] - S.fly[0], 0.2, -p, p);
      click(S.ins[1], 1, 1.05, p); click(S.ins[1] + 0.06, 0.6, 0.85, p); duck(S.ins[1]); sparkle(S.ins[1] + 0.05, 88, 0.05);
      click(S.clip[1] - 0.07, 0.5, 0.9, p); click(S.clip[1], 1.1, 1.0, p); duck(S.clip[1]); sparkle(S.clip[1] + 0.05, 91, 0.05);
      whoosh(S.snap[0] + 0.1, S.snap[1] - S.snap[0], 0.1, p, 0);
      click(S.snap[1], 1.4, 0.8, 0); boom(S.snap[1], 0.35); duck(S.snap[1], 0.35); sparkle(S.snap[1] + 0.06, 84, 0.09);
    }
    // finale
    riser(bt(58), TL.tada, 0.14);
    kick(TL.tada, 1); boom(TL.tada, 0.5); pad(TL.tada, DUR - 0.2, [48, 60, 64, 67, 72, 76], 0.07);
    sparkle(TL.tada + 0.02, 84, 0.11); sparkle(TL.tada + 0.5, 91, 0.07);
    for (let i = 0; i < 12; i++) { const t = TL.tada + 0.9 + i * B / 2; if (t < DUR - 1) pluck(t, [72, 76, 79, 84, 79, 76][i % 6], 0.05 * (1 - i / 14), i % 2 ? 0.4 : -0.4, 0.5); }
    master.gain.setValueAtTime(0.85, DUR - 2.2); master.gain.linearRampToValueAtTime(0.0001, DUR - 0.05);
    return ctx.startRendering();
  }
  let audioBuf = null;
  let audioP = null;
  const audioReady = () => audioP || (audioP = (async () => {
    if (!CAPTURE) try {   // the pre-rendered soundtrack (same synth, rendered once) loads instantly
      const r = await fetch('assembly_soundtrack.m4a'); if (!r.ok) throw 0;
      return (audioBuf = await new AudioContext().decodeAudioData(await r.arrayBuffer()));
    } catch (e) {}
    return (audioBuf = await score());
  })());
  async function wavBase64() {
    const b = await audioReady(), n = b.length, ch = [b.getChannelData(0), b.getChannelData(1)];
    const buf = new ArrayBuffer(44 + n * 4), dv = new DataView(buf);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVE'); w(12, 'fmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
    dv.setUint32(24, b.sampleRate, true); dv.setUint32(28, b.sampleRate * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
    for (let i = 0, o = 44; i < n; i++) for (let c = 0; c < 2; c++, o += 2) dv.setInt16(o, Math.max(-1, Math.min(1, ch[c][i])) * 32767, true);
    const u8 = new Uint8Array(buf); let s = '';
    for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    return btoa(s);
  }

  // ---------------------------------------------------------------- interactive player
  let playing = false, follow = true, last = 0, actx = null, src = null, muted = false, aT0 = 0, aC0 = 0;
  function startAudio() {
    if (!audioBuf || muted || !playing) return;
    if (!actx) actx = new AudioContext();
    stopAudio(); src = actx.createBufferSource(); src.buffer = audioBuf; src.connect(actx.destination);
    aT0 = T; aC0 = actx.currentTime + 0.02; src.start(aC0, T);
  }
  function stopAudio() { if (src) { try { src.stop(); } catch (e) {} src = null; } }
  let els = {};
  function ui() {
    const css = document.createElement('style'); css.textContent = `
      #bar { position:fixed; left:16px; right:16px; bottom:16px; display:flex; align-items:center; gap:10px; padding:10px 12px; flex-wrap:wrap;
             background:#1d1d21ee; border:1px solid #34343a; border-radius:14px; backdrop-filter:blur(10px); max-width:980px; margin:0 auto; color:#ecebe8; font:13px system-ui,sans-serif; }
      #bar button { background:#2a2a30; color:#ecebe8; border:1px solid #34343a; border-radius:999px; padding:7px 12px; font:inherit; cursor:pointer; }
      #bar button.pri { background:#f2a7c3; color:#1a1014; border-color:#f2a7c3; font-weight:700; min-width:76px; }
      #bar a { color:#f2a7c3; text-decoration:none; padding:7px 4px; }
      #track { position:relative; flex:1 1 260px; height:44px; }
      #track input { width:100%; margin:13px 0 0; accent-color:#f2a7c3; }
      #track .ch { position:absolute; top:-3px; font-size:10px; color:#9d9b95; transform:translateX(-50%); white-space:nowrap; cursor:pointer; }
      #time { font-variant-numeric:tabular-nums; color:#9d9b95; min-width:72px; }
      #big { position:fixed; left:50%; top:62%; transform:translate(-50%,-50%); background:#f2a7c3; color:#1a1014; border:0; border-radius:999px; padding:16px 28px;
             font:700 18px system-ui,sans-serif; cursor:pointer; box-shadow:0 10px 40px #0009; }
      #track .ch.lo { top:31px; }
      @media (max-width:700px) { #track .ch { display:none; } #bar { gap:6px; } }`;
    document.head.appendChild(css);
    const bar = document.createElement('div'); bar.id = 'bar';
    bar.innerHTML = `<button class="pri" id="pp">Play</button><div id="track"><input id="scrub" type="range" min="0" max="${DUR}" step="0.01" value="0"></div>
      <span id="time">0:00 / 0:44</span><button id="snd">Sound on</button><button id="cam">Camera: film</button>
      <a href="assembly.mp4" download>Video</a><a href="index.html">3D viewer</a>`;
    document.body.appendChild(bar);
    const big = document.createElement('button'); big.id = 'big'; big.textContent = 'Play with sound'; document.body.appendChild(big);
    els = { pp: bar.querySelector('#pp'), scrub: bar.querySelector('#scrub'), time: bar.querySelector('#time'), snd: bar.querySelector('#snd'), cam: bar.querySelector('#cam'), big };
    const track = bar.querySelector('#track');
    let ci = 0;
    for (const [label, t] of [['Print', bt(0.5)], ['One plate', bt(22)], ['Inner ear', bt(32)], ['Clip', bt(39)], ['Headband', bt(43)], ['Other side', bt(47)], ['Done', bt(59)]]) {
      const s = document.createElement('span'); s.className = 'ch' + (ci++ % 2 ? ' lo' : ''); s.textContent = label; s.style.left = (t / DUR * 100) + '%'; s.onclick = () => { seek(t); startAudio(); sync(); }; track.appendChild(s);
    }
    const play = async () => {
      if (T >= DUR - 0.05) seek(0);
      playing = true; big.remove(); last = performance.now(); sync();
      await audioReady(); startAudio();
    };
    big.onclick = play;
    els.pp.onclick = () => { if (playing) { playing = false; stopAudio(); sync(); } else play(); };
    els.scrub.oninput = () => { seek(+els.scrub.value); sync(); };
    els.scrub.onchange = () => startAudio();
    els.snd.onclick = () => { muted = !muted; if (muted) stopAudio(); else startAudio(); sync(); };
    els.cam.onclick = () => { follow = !follow; ctl.enabled = !follow; sync(); };
    canvas.addEventListener('pointerdown', () => { if (follow) { follow = false; ctl.enabled = true; sync(); } });
    ctl.enabled = false;
    audioReady();   // render the soundtrack in the background
    sync();
  }
  const fmt = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  function sync() {
    if (!els.pp) return;
    els.pp.textContent = playing ? 'Pause' : (T >= DUR - 0.05 ? 'Replay' : 'Play');
    els.scrub.value = T; els.time.textContent = `${fmt(T)} / ${fmt(DUR)}`;
    els.snd.textContent = muted ? 'Sound off' : 'Sound on'; els.cam.textContent = follow ? 'Camera: film' : 'Camera: free';
  }
  function frame(now) {
    if (!ready || CAPTURE) return;
    if (playing) {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      let t = T + dt;
      if (src && actx) t = aT0 + (actx.currentTime - aC0);   // lock the picture to the audio clock
      if (t >= DUR) { t = DUR; playing = false; stopAudio(); }
      apply(t); sync();
    } else { last = now; if (!follow) apply(T); }
    if (!follow) ctl.update();
    render();
  }
  window.__film = { DUR, seek: (t) => { seek(t); return true; }, wav: wavBase64 };
  return { attach, frame, get ready() { return ready; } };
})();
