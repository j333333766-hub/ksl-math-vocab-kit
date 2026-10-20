// 영상 만들기.ps1 이 영상 원본 html 에 넣어 쓰는 인코더. 찍어 둔 화면(JPEG)을 읽어 H.264로 묶어 mp4 를 만든다(Edge 안의 WebCodecs + mp4-muxer).
window.__rec = (() => {
  let muxer = null, enc = null, err = null, fps = 30, buf = null;
  return {
    async init(w, h, f) {
      fps = f;
      muxer = new Mp4Muxer.Muxer({ target: new Mp4Muxer.ArrayBufferTarget(), video: { codec: 'avc', width: w, height: h }, fastStart: 'in-memory' });
      enc = new VideoEncoder({ output: (c, m) => muxer.addVideoChunk(c, m), error: e => { err = String(e); } });
      const cfg = { codec: 'avc1.640028', width: w, height: h, bitrate: 3e6, bitrateMode: 'variable', framerate: f };
      if (!(await VideoEncoder.isConfigSupported(cfg)).supported) cfg.codec = 'avc1.42E028';
      enc.configure(cfg);
      return cfg.codec;
    },
    async encodeDir(base, n) {   // base 폴더의 00000.jpg … n.jpg 를 차례로 묶는다
      for (let i = 0; i <= n; i++) await this.add(await (await fetch(base + String(i).padStart(5, '0') + '.jpg')).blob(), i);
      return n;
    },
    async add(blob, i) {
      const bmp = await createImageBitmap(blob);
      const fr = new VideoFrame(bmp, { timestamp: Math.round(i * 1e6 / fps), duration: Math.round(1e6 / fps) });
      enc.encode(fr, { keyFrame: i % (fps * 2) === 0 }); fr.close(); bmp.close();
      for (let k = 0; enc.encodeQueueSize > 6; k++) { if (k > 2000) throw new Error('인코더가 멈췄어요(대기 ' + enc.encodeQueueSize + ', ' + enc.state + ')'); await new Promise(r => setTimeout(r, 5)); }
      if (err) throw new Error(err);
      return i;
    },
    async finish() { await enc.flush(); if (err) throw new Error(err); muxer.finalize(); buf = new Uint8Array(muxer.target.buffer); return buf.length; },
    part(k, size) {
      const s = buf.subarray(k * size, (k + 1) * size); let t = '';
      for (let i = 0; i < s.length; i += 0x8000) t += String.fromCharCode.apply(null, s.subarray(i, i + 0x8000));
      return btoa(t);
    }
  };
})();
