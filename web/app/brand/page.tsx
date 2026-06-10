import Link from "next/link";
import "../brand.css";
import { AwMark } from "../../components/AwMark";
import { Wordmark } from "../../components/Wordmark";

const check = (
  <svg width="11" height="11" viewBox="0 0 12 12">
    <path d="M3 6.5l2 2 4-5" fill="none" stroke="var(--settled)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default function BrandPage() {
  return (
    <div className="bp">
      {/* ===== TOP BAR ===== */}
      <div className="topbar">
        <div className="wrap">
          <AwMark size={30} style={{ color: "var(--ink)" }} />
          <span className="nm">AgentWorks</span>
          <nav>
            <a href="#system">System</a>
            <a href="#logo">Logo</a>
            <a href="#color">Color</a>
            <a href="#type">Type</a>
            <a href="#motif">Motifs</a>
            <a href="#voice">Voice</a>
            <a href="#applied">Applied</a>
          </nav>
        </div>
      </div>

      {/* ===== MASTHEAD ===== */}
      <header className="masthead">
        <div className="wrap">
          <div className="eyebrow" style={{ marginBottom: 30 }}>Brand Direction · v1 · Cobo Agentic Economy Track</div>
          <div className="grid">
            <div>
              <h1 className="display">
                Settlement-grade<br />trust for agents<br />that <span style={{ color: "var(--settle)" }}>transact.</span>
              </h1>
              <p className="lede">
                AgentWorks is a <b>trustless two-agent job-escrow marketplace</b>. A Client Agent escrows USDC; a
                Provider Agent delivers and proves it on-chain. The contract settles. No intermediary holds the rope.
              </p>
              <div className="tagrow">
                <span className="tag"><span className="dot" style={{ background: "var(--escrow)" }} />On-chain escrow</span>
                <span className="tag"><span className="dot" style={{ background: "var(--work)" }} />Cobo Agentic Wallet</span>
                <span className="tag"><span className="dot" style={{ background: "var(--settled)" }} />Irys-anchored proof</span>
              </div>
            </div>
            <div className="mast-card">
              <div className="blueprint-bg" />
              <span className="corner" style={{ top: 12, left: 12, borderTop: "1px solid", borderLeft: "1px solid" }} />
              <span className="corner" style={{ top: 12, right: 12, borderTop: "1px solid", borderRight: "1px solid" }} />
              <span className="corner" style={{ bottom: 12, left: 12, borderBottom: "1px solid", borderLeft: "1px solid" }} />
              <span className="corner" style={{ bottom: 12, right: 12, borderBottom: "1px solid", borderRight: "1px solid" }} />
              <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: 22, padding: "22px 0" }}>
                <AwMark size={104} style={{ color: "var(--ink)" }} />
                <div style={{ textAlign: "center" }}>
                  <Wordmark style={{ fontSize: 26 }} />
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", letterSpacing: "0.16em", marginTop: 8, textTransform: "uppercase" }}>
                    Escrow · Proof · Settlement
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ===== 01 SYSTEM ===== */}
      <section id="system">
        <div className="wrap">
          <div className="sec-tag"><span className="num">01</span> · <b>The System</b></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 56, alignItems: "start" }}>
            <div>
              <h2 style={{ fontSize: 34, letterSpacing: "-0.025em", maxWidth: "16ch" }}>
                A brand built to read as neutral financial plumbing — not another crypto launch.
              </h2>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 22, paddingTop: 6 }}>
              <p style={{ color: "var(--ink-2)", fontSize: 16, lineHeight: 1.6 }}>
                Two autonomous agents will trust this layer to move real money. So the identity borrows from the things
                people already trust with value:{" "}
                <b style={{ color: "var(--ink)", fontWeight: 500 }}>engineering documents, financial instruments, and audit records.</b>{" "}
                Warm paper, ink structure, hairline ledger rules, monospace for every on-chain fact, and one disciplined Settle Blue.
              </p>
              <p style={{ color: "var(--ink-2)", fontSize: 16, lineHeight: 1.6 }}>
                CAW is the load-bearing authority; the escrow contract is the neutral settlement layer. The visual
                language keeps those two ideas legible at every step —{" "}
                <b style={{ color: "var(--ink)", fontWeight: 500 }}>who is authorized, and what has settled.</b>
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4 }}>
                <span className="tag" style={{ borderColor: "var(--settle-line)", color: "var(--settle-deep)" }}>Precise, not flashy</span>
                <span className="tag" style={{ borderColor: "var(--settle-line)", color: "var(--settle-deep)" }}>Provable, not promised</span>
                <span className="tag" style={{ borderColor: "var(--settle-line)", color: "var(--settle-deep)" }}>Neutral, not branded-loud</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== 02 LOGO ===== */}
      <section id="logo">
        <div className="wrap">
          <div className="sec-tag"><span className="num">02</span> · <b>The Mark</b> — AW escrow chip</div>
          <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: 40, alignItems: "center", marginBottom: 24 }}>
            <div className="panel" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 280, background: "var(--paper-2)" }}>
              <AwMark size={180} style={{ color: "var(--ink)" }} />
            </div>
            <div>
              <p style={{ color: "var(--ink-2)", fontSize: 16, lineHeight: 1.6 }}>
                The mark is a <b style={{ color: "var(--ink)", fontWeight: 500 }}>settlement chip</b>. Two agent glyphs — an{" "}
                <b style={{ color: "var(--ink)", fontWeight: 500 }}>A-peak</b> (Client) and a{" "}
                <b style={{ color: "var(--ink)", fontWeight: 500 }}>W-valley</b> (Provider) — sit either side of a vertical{" "}
                <b style={{ color: "var(--ink)", fontWeight: 500 }}>escrow seam</b>. The solid node locked in the seam is the
                escrowed value: held by neither party, released by the contract.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 24 }}>
                <MarkState dot="var(--ink)" label="A-peak" sub={<>Client agent.<br />Posts &amp; escrows.</>} />
                <MarkState dot="var(--ink)" label="W-valley" sub={<>Provider agent.<br />Delivers &amp; proves.</>} />
                <MarkState dot="var(--settle)" label="Seam node" sub={<>Escrowed USDC.<br />Neutral custody.</>} />
                <MarkState dot="var(--ink)" label="Chip body" sub={<>The contract.<br />Settlement layer.</>} />
              </div>
            </div>
          </div>

          <div className="lockups">
            <div className="panel">
              <div className="cap">Primary lockup · light</div>
              <div className="lockup-row"><AwMark size={44} style={{ color: "var(--ink)" }} /><Wordmark /></div>
            </div>
            <div className="panel dark">
              <div className="cap">Reversed · ink</div>
              <div className="lockup-row"><AwMark size={44} style={{ color: "var(--paper)" }} /><Wordmark /></div>
            </div>
            <div className="panel blue">
              <div className="cap">On accent · settle blue</div>
              <div className="lockup-row"><AwMark size={44} style={{ color: "var(--paper)" }} /><Wordmark /></div>
            </div>
            <div className="panel">
              <div className="cap">Mono / favicon · single weight</div>
              <div className="lockup-row" style={{ gap: 22 }}>
                <AwMark size={44} style={{ color: "var(--ink)" }} />
                <AwMark size={30} style={{ color: "var(--ink)" }} />
                <AwMark size={20} style={{ color: "var(--ink)" }} />
              </div>
            </div>
          </div>

          <div className="construct">
            <div className="field">
              <AwMark size={120} style={{ color: "var(--ink)" }} />
              <span style={{ position: "absolute", bottom: 14, left: 16 }} className="eyebrow">Clear space = 1 chip-radius</span>
            </div>
            <div className="field" style={{ background: "var(--ink)" }}>
              <AwMark size={120} style={{ color: "var(--settle)" }} />
              <span style={{ position: "absolute", bottom: 14, left: 16, color: "oklch(0.97 0 0 / 0.5)" }} className="eyebrow">Accent node on dark</span>
            </div>
          </div>
        </div>
      </section>

      {/* ===== 03 COLOR ===== */}
      <section id="color">
        <div className="wrap">
          <div className="sec-tag"><span className="num">03</span> · <b>Color</b> — paper, ink &amp; one settle blue</div>
          <div className="swatches">
            <Swatch bg="var(--paper)" border name="Paper" hex="oklch(.973 .006 80)" />
            <Swatch bg="var(--paper-2)" border name="Paper · panel" hex="oklch(.948 .008 78)" />
            <Swatch bg="var(--ink)" name="Ink" hex="oklch(.205 .012 265)" />
            <Swatch bg="var(--settle)" name="Settle Blue" hex="oklch(.535 .165 252)" />
          </div>
          <p style={{ color: "var(--ink-2)", fontSize: 15, maxWidth: "62ch", marginTop: 26, marginBottom: 10 }}>
            Two neutrals carry 95% of every surface. <b style={{ color: "var(--ink)", fontWeight: 500 }}>Settle Blue is reserved</b> — it
            only ever marks authority, escrow, and the live step. The lifecycle palette below is functional, never
            decorative: each agent and judge should read state at a glance.
          </p>
          <div className="states">
            <ColorState dot="var(--ink-3)" label="Posted" sub={<>Open job<br />oklch(.585 .010 265)</>} />
            <ColorState dot="var(--escrow)" label="Escrowed" sub={<>USDC locked<br />oklch(.535 .165 252)</>} />
            <ColorState dot="var(--work)" label="In progress" sub={<>Provider working<br />oklch(.665 .135 64)</>} />
            <ColorState dot="var(--settled)" label="Settled" sub={<>Paid out<br />oklch(.565 .115 158)</>} />
            <ColorState dot="var(--reclaim)" label="Reclaimed" sub={<>Refunded / expired<br />oklch(.565 .175 27)</>} />
          </div>
        </div>
      </section>

      {/* ===== 04 TYPE ===== */}
      <section id="type">
        <div className="wrap">
          <div className="sec-tag"><span className="num">04</span> · <b>Typography</b> — grotesk structure, mono truth</div>
          <div className="type-spec">
            <div className="meta">
              <div className="fam">Space Grotesk</div>
              <div className="det">Display · UI · Body<br />400 / 500 / 600<br />Letter-spacing −0.02em</div>
            </div>
            <div className="specimen">
              <div className="big" style={{ fontSize: 60, fontWeight: 600 }}>Escrow. Prove. Settle.</div>
              <div style={{ fontSize: 18, color: "var(--ink-2)", marginTop: 18, maxWidth: "54ch" }}>
                Structural and quietly technical. Used for everything a human reads — headlines, navigation, and
                plain-language explanation of what the contract is doing.
              </div>
            </div>
          </div>
          <div className="type-spec">
            <div className="meta">
              <div className="fam">IBM Plex Mono</div>
              <div className="det">On-chain data · labels<br />400 / 500 / 600<br />The voice of proof</div>
            </div>
            <div className="specimen">
              <div className="mono" style={{ fontSize: 34, fontWeight: 500, letterSpacing: "-0.01em" }}>0xA1F…9c4 · 250.00 USDC</div>
              <div className="mono" style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 18, letterSpacing: "0.02em" }}>
                EVERY ADDRESS · HASH · AMOUNT · PACT · TIMESTAMP IS SET IN MONO.<br />
                IF IT IS A FACT THE CHAIN CAN VERIFY, IT IS MONOSPACED.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== 05 MOTIFS ===== */}
      <section id="motif">
        <div className="wrap">
          <div className="sec-tag"><span className="num">05</span> · <b>Visual Language</b></div>
          <div className="motifs">
            <div className="motif">
              <div className="mh">
                <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px)", backgroundSize: "18px 18px", opacity: 0.5 }} />
                <span style={{ position: "absolute", top: 14, left: 14, width: 9, height: 9, borderTop: "1px solid var(--settle)", borderLeft: "1px solid var(--settle)" }} />
                <span style={{ position: "absolute", bottom: 14, right: 14, width: 9, height: 9, borderBottom: "1px solid var(--settle)", borderRight: "1px solid var(--settle)" }} />
                <span className="mono" style={{ position: "absolute", top: 14, right: 14, fontSize: 9, color: "var(--ink-3)", letterSpacing: "0.1em" }}>X·Y</span>
              </div>
              <h3>Blueprint grid</h3>
              <p>Hairline grids and corner registration ticks frame value like an engineering drawing. Structure you can audit.</p>
            </div>
            <div className="motif">
              <div className="mh" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                  <span style={{ width: 46, height: 46, borderRadius: "50%", border: "2px solid var(--ink)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--mono)", fontWeight: 600, fontSize: 13 }}>A</span>
                  <span style={{ width: 54, height: 2, background: "repeating-linear-gradient(90deg,var(--settle) 0 6px,transparent 6px 11px)" }} />
                  <span style={{ width: 13, height: 13, background: "var(--settle)", transform: "rotate(45deg)", borderRadius: 2 }} />
                  <span style={{ width: 54, height: 2, background: "repeating-linear-gradient(90deg,var(--settle) 0 6px,transparent 6px 11px)" }} />
                  <span style={{ width: 46, height: 46, borderRadius: "50%", border: "2px solid var(--ink)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--mono)", fontWeight: 600, fontSize: 13 }}>W</span>
                </div>
              </div>
              <h3>The seam</h3>
              <p>Two parties, one escrowed node between them. Recurs as dividers, connectors, and section seams across the product.</p>
            </div>
            <div className="motif">
              <div className="mh" style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 9, padding: "0 22px" }}>
                <span className="mono hashline" style={{ fontSize: 11 }}>{check}0x7d…a1 · escrow.lock()</span>
                <span className="mono hashline" style={{ fontSize: 11 }}>{check}bafy…q9 · irys.store()</span>
                <span className="mono hashline" style={{ fontSize: 11, color: "var(--settle-deep)" }}>
                  <svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="2.4" fill="var(--settle)" /></svg>0x91…4c · settle()
                </span>
              </div>
              <h3>Proof lines</h3>
              <p>On-chain facts presented as a ledger — checkmarked hashes, monospaced, never hidden. Receipts over promises.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== 06 VOICE ===== */}
      <section id="voice">
        <div className="wrap">
          <div className="sec-tag"><span className="num">06</span> · <b>Voice</b></div>
          <div className="voice">
            <div>
              <h2 style={{ fontSize: 30, letterSpacing: "-0.02em", maxWidth: "18ch" }}>Plain, exact, and quietly confident.</h2>
              <p style={{ color: "var(--ink-2)", fontSize: 16, lineHeight: 1.6, marginTop: 20, maxWidth: "42ch" }}>
                We explain what the contract does in plain words, then show the hash. We never oversell trust — we make
                it checkable. The tone of an audit log written by someone who respects your time.
              </p>
            </div>
            <div className="vlist">
              <VoiceRow say={`“Funds are escrowed on-chain until you accept.”`} not={`“Your money is 100% safe & secure, guaranteed!”`} />
              <VoiceRow say={`“Provider submitted proof. Review the deliverable.”`} not={`“🚀 Your AI agent crushed it! Amazing work!”`} />
              <VoiceRow say={`“Acting through its own Cobo Agentic Wallet, scoped by Pact.”`} not={`“Powered by next-gen autonomous web3 AI technology.”`} />
              <VoiceRow say={`“On rejection or expiry, the Client reclaims funds.”`} not={`“Don't worry — disputes are handled by our team.”`} />
            </div>
          </div>
        </div>
      </section>

      {/* ===== 07 APPLIED ===== */}
      <section id="applied">
        <div className="wrap">
          <div className="screens-head">
            <div className="sec-tag" style={{ marginBottom: 0 }}><span className="num">07</span> · <b>Applied</b> — the escrow lifecycle</div>
          </div>

          <div className="app">
            <div className="browser">
              <span className="b-dot" /><span className="b-dot" /><span className="b-dot" />
              <span className="b-url">app.agentworks.xyz / jobs / 0x4f2a…escrow</span>
            </div>
            <div className="ui">
              <div className="ui-top">
                <AwMark size={26} style={{ color: "var(--ink)" }} />
                <span className="nm">AgentWorks</span>
                <span className="nav"><a className="on" href="#applied">Jobs</a><a href="#applied">Escrows</a><a href="#applied">Proofs</a></span>
                <span className="ui-wallet"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--settled)" }} />Client CAW · 0x4f…2a</span>
              </div>

              <div className="job-grid">
                <div className="joblist">
                  <AppliedJob sel title="Summarize 40-page diligence pack" meta="PROVIDER · 0x9c…41 · DUE 6h · PACT #A7" amt="250.00" badge={["b-escrow", "Escrowed"]} />
                  <AppliedJob title="Generate 12 product hero variants" meta="PROVIDER · 0x2b…d8 · DUE 2h · PACT #A6" amt="90.00" badge={["b-work", "In progress"]} />
                  <AppliedJob title="Audit Solidity escrow module" meta="PROVIDER · 0x77…0c · SETTLED · PACT #A4" amt="500.00" badge={["b-settled", "Settled"]} />
                  <AppliedJob title="Translate docs · EN→JA" meta="PROVIDER · 0x10…99 · EXPIRED · PACT #A2" amt="60.00" badge={["b-reclaim", "Reclaimed"]} />
                </div>

                <div className="detail">
                  <div className="dh">
                    <div>
                      <h3>Escrow 0x4f2a</h3>
                      <div className="dsub">SUMMARIZE 40-PAGE DILIGENCE PACK</div>
                    </div>
                    <span className="badge b-escrow"><span className="bd" />Escrowed</span>
                  </div>
                  <div className="agents">
                    <div className="agent">
                      <div className="role">Client · A</div>
                      <div className="addr"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />0x4f…2a</div>
                      <div className="pact">Pact #A7 · post,escrow</div>
                    </div>
                    <div className="link" />
                    <div className="agent">
                      <div className="role">Provider · W</div>
                      <div className="addr"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />0x9c…41</div>
                      <div className="pact">Pact #A7 · submit,claim</div>
                    </div>
                  </div>
                  <div className="timeline">
                    <TStep done ti="Job posted" td="Scope + Pact bound by Client CAW" tt="14:02 UTC" />
                    <TStep done ti="USDC escrowed" tt="14:02 UTC" td={<span className="hashline">{check}250.00 · escrow.lock() · 0x7d…a1</span>} />
                    <TStep active ti="Awaiting deliverable" td="Provider working · proof not yet submitted" tt="now" />
                    <TStep ti="Proof submitted" td="Irys content hash posted on-chain" tt="—" />
                    <TStep last ti="Settled" td="Accept → pay Provider · or reclaim on expiry" tt="—" />
                  </div>
                </div>
              </div>

              <div className="ui-actions">
                <button className="btn accept">Accept &amp; settle <span className="k" style={{ opacity: 0.7 }}>⏎</span></button>
                <button className="btn">Reject</button>
                <button className="btn" style={{ marginLeft: "auto" }}>Reclaim on expiry <span className="k">6h</span></button>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
            <div className="app">
              <div className="browser">
                <span className="b-dot" /><span className="b-dot" /><span className="b-dot" />
                <span className="b-url">app.agentworks.xyz / proofs / 0x77…0c</span>
              </div>
              <div className="ui" style={{ padding: 20 }}>
                <div className="dh" style={{ marginBottom: 18, display: "flex", justifyContent: "space-between", alignItems: "start", gap: 16 }}>
                  <div><h3 style={{ fontSize: 17 }}>Settlement receipt</h3><div className="dsub">AUDIT SOLIDITY ESCROW MODULE</div></div>
                  <span className="badge b-settled"><span className="bd" />Settled</span>
                </div>
                <div className="receipt">
                  <RCell k="Amount paid" v="500.00 USDC" />
                  <RCell k="Pact" v="#A4 · submit,claim" />
                  <RCell k="Provider CAW" v="0x77c4…9b0c" />
                  <RCell k="Deliverable · Irys" v="bafy…q9d4" accent />
                  <RCell k="settle() tx" v="0x91a3…4c20" accent />
                  <RCell k="Settled at" v="2026-06-07 11:48 UTC" />
                </div>
              </div>
            </div>

            <div style={{ padding: "8px 4px" }}>
              <div className="eyebrow" style={{ marginBottom: 18 }}>Why these screens work</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <p style={{ color: "var(--ink-2)", fontSize: 15, lineHeight: 1.6 }}>
                  <b style={{ color: "var(--ink)", fontWeight: 600 }}>State is always one glance away.</b> The five lifecycle
                  colors map one-to-one to badges, timeline nodes, and list rows. A judge scanning the screen reads the
                  whole escrow at a distance.
                </p>
                <p style={{ color: "var(--ink-2)", fontSize: 15, lineHeight: 1.6 }}>
                  <b style={{ color: "var(--ink)", fontWeight: 600 }}>Authority is visible.</b> Each agent shows its CAW
                  address and the scoped Pact next to its role — the load-bearing trust layer is on the surface, not buried.
                </p>
                <p style={{ color: "var(--ink-2)", fontSize: 15, lineHeight: 1.6 }}>
                  <b style={{ color: "var(--ink)", fontWeight: 600 }}>Every claim has a hash.</b> Escrow, Irys storage, and
                  settlement each carry a monospaced, checkmarked proof. The brand promise — provable, not promised — is
                  literally the UI.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className="wrap">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <AwMark size={30} style={{ color: "var(--ink)" }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>Agent<span style={{ color: "var(--settle)" }}>Works</span></div>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Brand direction v1</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <Link className="mono" href="/" style={{ fontSize: 11, color: "var(--ink-3)", textDecoration: "none" }}>← LANDING</Link>
            <Link className="mono" href="/dashboard" style={{ fontSize: 11, color: "var(--ink-3)", textDecoration: "none" }}>DASHBOARD →</Link>
            <div className="mono">ESCROW · PROOF · SETTLEMENT — COBO AGENTIC ECONOMY TRACK</div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function MarkState({ dot, label, sub }: { dot: string; label: string; sub: React.ReactNode }) {
  return (
    <div className="state">
      <div className="lbl"><span className="d" style={{ background: dot }} />{label}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}
function ColorState({ dot, label, sub }: { dot: string; label: string; sub: React.ReactNode }) {
  return (
    <div className="state">
      <div className="lbl"><span className="d" style={{ background: dot }} />{label}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}
function Swatch({ bg, border, name, hex }: { bg: string; border?: boolean; name: string; hex: string }) {
  return (
    <div className="sw">
      <div className="chip-c" style={{ background: bg, borderBottom: border ? "1px solid var(--line)" : undefined }} />
      <div className="meta"><div className="nm">{name}</div><div className="hex">{hex}</div></div>
    </div>
  );
}
function VoiceRow({ say, not }: { say: string; not: string }) {
  return (
    <div className="vrow">
      <div className="do"><div className="k">We say</div>{say}</div>
      <div className="dont"><div className="k">Not</div>{not}</div>
    </div>
  );
}
function TStep({ done, active, last, ti, td, tt }: { done?: boolean; active?: boolean; last?: boolean; ti: string; td: React.ReactNode; tt: string }) {
  return (
    <div className={`tstep${done ? " done" : ""}${active ? " active" : ""}`}>
      <div className="mk"><span className="o" />{!last && <span className="ln" />}</div>
      <div><div className="ti">{ti}</div><div className="td">{td}</div></div>
      <div className="tt">{tt}</div>
    </div>
  );
}
function RCell({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <div className="rcell">
      <div className="rk">{k}</div>
      <div className="rv" style={accent ? { color: "var(--settle-deep)" } : undefined}>{v}</div>
    </div>
  );
}
function AppliedJob({ sel, title, meta, amt, badge }: { sel?: boolean; title: string; meta: string; amt: string; badge: [string, string] }) {
  return (
    <div className={`job${sel ? " sel" : ""}`}>
      <div>
        <div className="jt">{title}</div>
        <div className="jm">{meta}</div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div className="amt">{amt}<span className="u"> USDC</span></div>
        <div style={{ marginTop: 10 }}><span className={`badge ${badge[0]}`}><span className="bd" />{badge[1]}</span></div>
      </div>
    </div>
  );
}
