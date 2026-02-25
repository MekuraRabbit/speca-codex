#3
Invalid.

#5
From Grandine team:

As the expect says, "MIN_ATTESTATION_INCLUSION_DELAY is at least 1 in all presets". Attestations with slots that violate MIN_ATTESTATION_INCLUSION_DELAY requirement are not accepted in fork choice (they are delayed instead), and will never appear in RealSlotReport::update_performance. This is a non-issue.

Correction: "included in block" instead of "accepted in fork choice (they are delayed instead)".

SlotReport::update_performance is only called in state transition, and only after attestations are validated. And during validations MIN_ATTESTATION_INCLUSION_DELAY is checked:
attestation_slot + P::MIN_ATTESTATION_INCLUSION_DELAY.get() <= state.slot()

#7
From the EF team:

initialize_shuffled_indices is used in state transition functions only, it initializes the new state's internal shuffling cache. The desired behaviour of state transition is to reject the block on first validation failure encountered.

initialize_shuffled_indices works as it was designed, block can only contain attestations that are not older than MIN_ATTESTATION_INCLUSION_DELAY, it definitely cannot include earlier attestations than from previous epoch.

The proposed mitigation not only tries to solve non-existing issue, it also can be considered harmful, as it will proceed with shuffling initialization with invalid attestations instead of exiting early and thus degrading the performance.

#8
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.
The PR https://github.com/ethereum/go-ethereum/pull/32641 was created one day before the issue submission. Also, the Geth team has explicitly stated that they won't fix this issue. Planning to keep as invalid.


#12
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.
From the Reth team:

no fix, so invalid per contest rules

Keeping as invalid.

#13
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

From the Erigon team:

Invalid as no fix

Keeping as invalid.

#14
I don’t think this issue was introduced by Fusaka. It should be submitted to the EF bounty instead. Also, this issue is a design suggestion rather than a real security issue — it relies on other potential vulnerabilities to have any impact.

#17
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

From the Geth team:

Invalid as no fix

#21
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

Invalid as no fix.

#22
Attacker (or bad/corrupt disk) ensures the node stores or is asked to serve a header whose RLP encoding triggers an error.
Remote peer sends a contiguous GetBlockHeaders request that includes the problematic header in the served range (either by number or by hash origin).
serviceContiguousBlockHeaderQuery calls rlp.EncodeToBytes(header) and discards the returned error.
Because the error is ignored the function either:
appends an invalid/zero rlp.RawValue into the response (if encoding returned nil bytes), or
continues and later returns a partial/malformed header list, or
if the encode failure indicates deeper corruption, the node may panic elsewhere or produce inconsistent network responses.
The remote peer receives incorrect/malformed header data (or the node experiences an internal failure), which can cause downstream sync failures, misbehaviour detection, or require operator intervention (resync).

The attack path is overly abstract and relies on too many assumptions. This attack path does not cause any impact on entities other than the attacker — if the attacker intentionally or due to disk factors produces bad data, other nodes will simply reject the payload. This would not trigger downstream sync failures on other nodes.

In addition, issues of Low severity or higher must be submitted along with a PoC.
Invalid as no fix.


#23
The Nethermind team doesn’t plan to fix this comment issue. planning to keep it as invalid.


#25
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

Invalid as no fix

#27
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

Invalid as no fix.

#28
potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

Invalid as no fix

#30
Keeping as invalid. for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

#31
Osaka blob parameters differ from Prague
User sends blob transactions >max in Prague
Chain split as Besu rejects a block while other clients accept

Agree with the protocol team’s judgement. The configuration described by Watson will not occur. Considering other clients are deprecating support, limiting blob schedule changes to BPO forks only, I believe this is a valid design choice.

#32
Out of scope. Issue was not introduced in Fusaka.

#33
Client comment:

#33 is invalid.

curl -s -X POST localhost:8545 -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":3,"method":"eth_estimateGas","params":[{"from":"0x0000000000000000000000000000000000000001","to":"0x0000000000000000000000000000000000000002","gas":"0x1000001"}]}'
{"jsonrpc":"2.0","id":3,"error":{"code":-32000,"message":"gas limit too high: address 0x0000000000000000000000000000000000000001, gas limit 16777217"}}

Running with

./build/bin/erigon --override.osaka=0

#35
This does describe a good test case for boundary testing, but in terms of what's possible on a network, its not really possible IMO

Keeping as invalid. For issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

#36
Out of scope, the issue was not introduced in Fusaka.

#37
Invalid as it wasn't introduced by Fusaka upgrade.

#38
This issue was not introduced by the Fusaka upgrade. Planning to keep it as invalid because it’s OOS.

#39
From Nimbus team:

here the custody subnets and the custody group counts exactly end up to be the same value, numerically, so even if the peer searches for custody subnets and matches them with custody group count (fetched from the ENR), it should be totally fine, the reason being, right now there's 1 column per subnet. for 39, i feel it's invalid

Planning to keep this as invalid.

#42
This issue has no impact, and the protocol team does not plan to fix it. Planning to keep as invalid.

#43
This issue has no impact, and the protocol team does not plan to fix it. Planning to keep as invalid.

#47
The impact of this issue does not meet our requirements for L/M/H severity

Vulnerabilities that allow an attacker to slash more than 0.01% of validators, trivially cause network splits affecting at least 0.01% of the network, or being able to bring down more than 0.01% of the network by sending a single network packet or an on-chain transaction.

The node can experience increased latency or temporary stalls in forkchoice updates and block processing. This is an availability degradation; depending on timing and load, it could manifest as delayed head updates or missed performance targets.

Keeping as potential info, but remains invalid as for issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

#54
From Geth team:

I triaged issue #54, its another invalid. There is no case where the parent header has ExcessBlobGas set without also having BlobGasUsed set. If BlobGasUsed is 0, it will be set to 0 not to nil

Planning to keep this as invalid.

#57
Keeping as invalid. For issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

#58
Client comment:

This is a non-issue in my opinion. If a peer claims to custody some columns it doesn't actually custody, it will be de-peered via downscoring pretty quickly. A realistic attack scenario would require the attacker spin up a very large number of nodes. Unless they can prove this is worth fixing, I would consider it an invalid finding.

The report was submitted as info and did not prove this can reach a higher severity. If you still believe this issue can be a valid low, please submit a high-level attack path and a PoC. The Prysm team is currently unwilling to fix it, so we will keep it as invalid.

#59
This issue describes an overly abstract scenario and lacks high-level supporting evidence. Agree with the protocol team’s judgement.

#61
Agree with the protocol team's judgement. Keeping as invalid.

Invalid as no fix.

#62
Agree this issue was not introduced by Fusaka and should be submitted to the EF bounty instead.

#63
Keeping as invalid. For issue to be valid info, it requires a client to fix the issue. It will be invalid unless fixed.

#67
From Geth team:

invalid: We are aware of this and using the deprecated API does not make it unsafe.

Planning to keep as invalid.