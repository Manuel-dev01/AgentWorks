import asyncio, json, time
import config, registry, pacts
import escrow_v4 as esc
import reasoning, irys_store
from caw.client import CawWallet
from uuid import uuid4

JOB = 7

def judge_with_retry(spec, deliverable, name, llm, tries=5):
    last = None
    for i in range(tries):
        try:
            return reasoning.evaluate_member(spec, deliverable, member_name=name, llm=llm)
        except Exception as e:
            last = e; print(f'  [{name}] judge attempt {i+1} failed: {type(e).__name__}; retrying'); time.sleep(4*(i+1))
    raise RuntimeError(f'{name} judging failed after {tries}: {last}')

async def main():
    w3 = esc.web3()
    d = json.load(open('scripts/.market/runs/7.json'))
    deliverable = d['deliverable']
    spec = f"{d['task']}\n\nAcceptance criteria: {d.get('criteria','')}"
    j = esc.get_job(w3, JOB)
    assert irys_store.keccak(deliverable.encode()).lower() == (j['deliverable_hash'] or '').lower(), 'hash mismatch'
    members = registry.evaluators()
    print('job#7 status', j['status'], '| quorum', config.COMMITTEE_QUORUM)
    approvals = 0; vote_txs = {}
    for m in members:
        v = esc.get_vote(w3, JOB)
        if v['approve'] >= config.COMMITTEE_QUORUM:
            print('quorum reached, stopping'); break
        jn = esc.get_job(w3, JOB)
        if jn['status'] != 'Submitted':
            print('job left Submitted, stopping'); break
        if esc.has_member_voted(w3, JOB, m.address):
            print(f'[{m.name}] already voted'); continue
        verdict = judge_with_retry(spec, deliverable, m.name, m.llm())
        approve = bool(verdict.get('accept'))
        print(f'[{m.name}] model={m.llm()["model"]} -> accept={approve}')
        async with CawWallet(api_url=config.CAW_API_URL, api_key=m.api_key, wallet_uuid=m.wallet_id, name=m.name) as root:
            sub = await root.submit_pact(intent=f"{m.name} recovery vote",
                                         spec=pacts.evaluator_pact(escrow=config.ESCROW_V4_ADDRESS),
                                         name=f"rec7-{m.name.replace(' ','')}-{uuid4().hex[:5]}")
            pact = await root.wait_pact_active(sub.get('pact_id'))
            async with root.scoped(pact, name_suffix="") as ew:
                rid = f"rec7-{uuid4().hex[:8]}"
                resp = await ew.contract_call(src_addr=m.address, contract_addr=config.ESCROW_V4_ADDRESS,
                                              calldata=esc.cast_vote(JOB, approve), chain_id=config.CHAIN_ID,
                                              request_id=rid, description=f"castVote[{m.name}]")
                rec = await ew.wait_tx_final(rid, timeout=300.0)
                h = (rec or {}).get('transaction_hash') or (resp or {}).get('transaction_hash')
                ok = (rec or {}).get('status_display') == 'Success'
                print(f'[{m.name}] castVote tx={h} success={ok}')
                if ok and approve:
                    approvals += 1; vote_txs[m.name] = {'addr': m.address, 'model': m.llm()['model'], 'tx': h}
    v = esc.get_vote(w3, JOB); j = esc.get_job(w3, JOB)
    print('\n=== RESULT ==='); print('status', j['status'], '| votes', v['approve'],'-',v['reject'], '| tentative_payout', v['tentative_payout'])
    print(json.dumps(vote_txs, indent=2))

asyncio.run(main())
