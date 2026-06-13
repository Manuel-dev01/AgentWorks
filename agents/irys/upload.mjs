// Irys devnet uploader - reads deliverable from stdin, prints {id,url,...} as JSON.
// Env: IRYS_PRIVATE_KEY (or DEPLOYER_PRIVATE_KEY), RPC_URL. Tags: argv[2] = JSON [{name,value}].
import Uploader from "@irys/upload";
import Ethereum from "@irys/upload-ethereum";

function readStdin() {
  return new Promise((resolve) => {
    let d = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (d += c));
    process.stdin.on("end", () => resolve(d));
  });
}

const raw = process.env.IRYS_PRIVATE_KEY || process.env.DEPLOYER_PRIVATE_KEY;
if (!raw) {
  console.log(JSON.stringify({ error: "missing IRYS_PRIVATE_KEY / DEPLOYER_PRIVATE_KEY" }));
  process.exit(1);
}
const pk = raw.startsWith("0x") ? raw : "0x" + raw;
const rpc = process.env.RPC_URL || "https://sepolia.drpc.org";
const tags = process.argv[2] ? JSON.parse(process.argv[2]) : [];

const data = await readStdin();
const bytes = Buffer.byteLength(data);

const irys = await Uploader(Ethereum).withWallet(pk).withRpc(rpc).devnet();

let price = "0", funded = "0";
try {
  const p = await irys.getPrice(bytes);
  price = p.toString();
  const bal = await irys.getLoadedBalance();
  if (bal.lt(p)) {
    const f = await irys.fund(p.minus(bal));
    funded = String(f && (f.quantity ?? f));
  }
} catch (e) {
  // pricing/funding is best-effort; tiny uploads are often free. If upload truly needs funds it throws below.
}

const receipt = await irys.upload(data, { tags });
console.log(JSON.stringify({ id: receipt.id, url: `https://devnet.irys.xyz/${receipt.id}`, bytes, price, funded }));
