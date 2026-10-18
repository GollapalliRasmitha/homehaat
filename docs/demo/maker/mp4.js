// Minimal MP4 writer for one H.264 video track + one AAC audio track (moov first, so it starts playing at once).
// Samples come from WebCodecs (VideoEncoder with avc format, AudioEncoder with aac).
(function () {
  const te = new TextEncoder();
  const u32 = (n) => [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255];
  const u16 = (n) => [(n >>> 8) & 255, n & 255];
  const str = (s) => [...te.encode(s)];
  function box(type, ...parts) {
    const body = parts.flat(Infinity);
    return [...u32(body.length + 8), ...str(type), ...body];
  }
  const full = (type, version, flags, ...parts) => box(type, [version, (flags >> 16) & 255, (flags >> 8) & 255, flags & 255], ...parts);
  const matrix = [...u32(0x10000), ...u32(0), ...u32(0), ...u32(0), ...u32(0x10000), ...u32(0), ...u32(0), ...u32(0), ...u32(0x40000000)];

  function stbl(entry, samples, timescaleDelta, offsets, withSync) {
    const stts = full("stts", 0, 0, u32(1), u32(samples.length), u32(timescaleDelta));
    const stsc = full("stsc", 0, 0, u32(1), u32(1), u32(1), u32(1)); // one sample per chunk
    const stsz = full("stsz", 0, 0, u32(0), u32(samples.length), samples.map((s) => u32(s.data.length)));
    const stco = full("stco", 0, 0, u32(offsets.length), offsets.map((o) => u32(o)));
    const parts = [full("stsd", 0, 0, u32(1), entry), stts, stsc, stsz, stco];
    if (withSync) {
      const keys = samples.map((s, i) => (s.key ? i + 1 : 0)).filter(Boolean);
      parts.splice(2, 0, full("stss", 0, 0, u32(keys.length), keys.map((k) => u32(k))));
    }
    return box("stbl", ...parts);
  }
  const dinf = () => box("dinf", full("dref", 0, 0, u32(1), full("url ", 0, 1)));

  function esds(asc, bitrate) {
    const dec = [0x05, asc.length, ...asc];
    const dcd = [0x04, 13 + dec.length, 0x40, 0x15, 0, 0, 0, ...u32(bitrate), ...u32(bitrate), ...dec];
    const es = [0x03, 3 + dcd.length + 3, ...u16(1), 0, ...dcd, 0x06, 1, 0x02];
    return full("esds", 0, 0, es);
  }

  /** video: {width,height,timescale,frameTicks,avcC:Uint8Array,samples:[{data,key}]}; audio: {sampleRate,channels,asc,bitrate,samples:[{data}]} */
  window.writeMp4 = function (video, audio) {
    const durMs = Math.round((video.samples.length * video.frameTicks * 1000) / video.timescale);
    const build = (base) => {
      let pos = base;
      const vOff = video.samples.map((s) => { const o = pos; pos += s.data.length; return o; });
      const aOff = audio ? audio.samples.map((s) => { const o = pos; pos += s.data.length; return o; }) : [];
      const avc1 = box("avc1", [0, 0, 0, 0, 0, 0], u16(1), u16(0), u16(0), u32(0), u32(0), u32(0), u16(video.width), u16(video.height),
        u32(0x00480000), u32(0x00480000), u32(0), u16(1), new Array(32).fill(0), u16(0x18), u16(0xffff), box("avcC", [...video.avcC]));
      const vtrak = box("trak",
        full("tkhd", 0, 3, u32(0), u32(0), u32(1), u32(0), u32(durMs), u32(0), u32(0), u16(0), u16(0), u16(0), u16(0), matrix, u32(video.width << 16), u32(video.height << 16)),
        box("mdia",
          full("mdhd", 0, 0, u32(0), u32(0), u32(video.timescale), u32(video.samples.length * video.frameTicks), u16(0x55c4), u16(0)),
          full("hdlr", 0, 0, u32(0), str("vide"), u32(0), u32(0), u32(0), str("VideoHandler"), [0]),
          box("minf", full("vmhd", 0, 1, u16(0), u16(0), u16(0), u16(0)), dinf(), stbl(avc1, video.samples, video.frameTicks, vOff, true))));
      let atrak = [];
      if (audio) {
        const mp4a = box("mp4a", [0, 0, 0, 0, 0, 0], u16(1), u32(0), u32(0), u16(audio.channels), u16(16), u16(0), u16(0), u32(audio.sampleRate << 16), esds([...audio.asc], audio.bitrate));
        const aDur = audio.samples.length * 1024;
        atrak = box("trak",
          full("tkhd", 0, 3, u32(0), u32(0), u32(2), u32(0), u32(Math.round((aDur * 1000) / audio.sampleRate)), u32(0), u32(0), u16(0), u16(1), u16(0x0100), u16(0), matrix, u32(0), u32(0)),
          box("mdia",
            full("mdhd", 0, 0, u32(0), u32(0), u32(audio.sampleRate), u32(aDur), u16(0x55c4), u16(0)),
            full("hdlr", 0, 0, u32(0), str("soun"), u32(0), u32(0), u32(0), str("SoundHandler"), [0]),
            box("minf", full("smhd", 0, 0, u16(0), u16(0)), dinf(), stbl(mp4a, audio.samples, 1024, aOff, false))));
      }
      const mvhd = full("mvhd", 0, 0, u32(0), u32(0), u32(1000), u32(durMs), u32(0x10000), u16(0x0100), u16(0), u32(0), u32(0), matrix, new Array(24).fill(0), u32(audio ? 3 : 2));
      return box("moov", mvhd, vtrak, atrak);
    };
    const ftyp = box("ftyp", str("isom"), u32(512), str("isom"), str("iso2"), str("avc1"), str("mp41"));
    const moovSize = build(0).length; // the box sizes don't depend on the offsets' values
    const mdatSize = 8 + video.samples.reduce((n, s) => n + s.data.length, 0) + (audio ? audio.samples.reduce((n, s) => n + s.data.length, 0) : 0);
    const moov = build(ftyp.length + moovSize + 8);
    const out = new Uint8Array(ftyp.length + moov.length + mdatSize);
    let p = 0;
    out.set(ftyp, p); p += ftyp.length;
    out.set(moov, p); p += moov.length;
    out.set([...u32(mdatSize), ...str("mdat")], p); p += 8;
    for (const s of video.samples) { out.set(s.data, p); p += s.data.length; }
    if (audio) for (const s of audio.samples) { out.set(s.data, p); p += s.data.length; }
    return out;
  };
})();
