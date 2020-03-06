import pytest
from eth_tester.exceptions import TransactionFailed

from plasma_core.constants import NULL_ADDRESS
from plasma_core.utils.transactions import decode_utxo_id, encode_utxo_id
from tests_utils.constants import PAYMENT_TX_MAX_INPUT_SIZE, PAYMENT_TX_MAX_OUTPUT_SIZE


@pytest.mark.parametrize(
    "double_spend_output_index,challenge_input_index",
    [(i, j) for i in range(PAYMENT_TX_MAX_OUTPUT_SIZE) for j in range(PAYMENT_TX_MAX_INPUT_SIZE)]
)
def test_challenge_in_flight_exit_not_canonical_should_succeed(testlang, double_spend_output_index, challenge_input_index):
    alice, bob, carol = testlang.accounts[0], testlang.accounts[1], testlang.accounts[2]
    deposit_amount = 100
    deposit_id = testlang.deposit(alice, deposit_amount)

    tx_output_amount = deposit_amount // PAYMENT_TX_MAX_OUTPUT_SIZE
    outputs = [(alice.address, NULL_ADDRESS, tx_output_amount)] * PAYMENT_TX_MAX_OUTPUT_SIZE

    input_tx_id = testlang.spend_utxo([deposit_id], [alice], outputs=outputs)
    blknum, tx_index, _ = decode_utxo_id(input_tx_id)
    double_spend_utxo = encode_utxo_id(blknum, tx_index, double_spend_output_index)

    ife_output_amount = tx_output_amount
    ife_tx_id = testlang.spend_utxo(
        [double_spend_utxo],
        [alice],
        [(bob.address, NULL_ADDRESS, ife_output_amount)]
    )

    inputs = []
    for i in range(0, PAYMENT_TX_MAX_INPUT_SIZE):
        if i == challenge_input_index:
            inputs.append(double_spend_utxo)
        else:
            inputs.append(testlang.deposit(alice, tx_output_amount))

    challenge_tx_id = testlang.spend_utxo(
        inputs,
        [alice] * PAYMENT_TX_MAX_INPUT_SIZE,
        [
            (carol.address, NULL_ADDRESS, tx_output_amount),
        ],
        force_invalid=True
    )

    testlang.start_in_flight_exit(ife_tx_id)

    testlang.challenge_in_flight_exit_not_canonical(ife_tx_id, challenge_tx_id, account=carol)

    in_flight_exit = testlang.get_in_flight_exit(ife_tx_id)
    assert in_flight_exit.bond_owner == carol.address
    assert in_flight_exit.oldest_competitor == challenge_tx_id
    assert not in_flight_exit.is_canonical


def test_challenge_in_flight_exit_not_canonical_wrong_period_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                          force_invalid=True)

    testlang.start_in_flight_exit(spend_id)
    testlang.forward_to_period(2)

    with pytest.raises(TransactionFailed):
        testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id, account=owner_2)


def test_challenge_in_flight_exit_not_canonical_same_tx_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)], force_invalid=True)

    testlang.start_in_flight_exit(spend_id)

    with pytest.raises(TransactionFailed):
        testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id, account=owner_2)


@pytest.mark.parametrize("deposit_as_input", [0, 1])
def test_challenge_in_flight_exit_not_canonical_unrelated_tx_should_fail(testlang, deposit_as_input):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id_1 = testlang.deposit(owner_1, amount)
    deposit_id_2 = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id_1], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    unrelated_spend_id = testlang.spend_utxo([deposit_id_2], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    spend_tx = testlang.child_chain.get_transaction(spend_id)
    unrelated_spend_tx = testlang.child_chain.get_transaction(unrelated_spend_id)

    testlang.start_in_flight_exit(spend_id)

    proof = testlang.get_merkle_proof(unrelated_spend_id)
    signature = unrelated_spend_tx.signatures[0]

    if deposit_as_input == 0:
        input_tx_id = deposit_id_1
    else:
        input_tx_id = deposit_id_2
    input_tx = testlang.child_chain.get_transaction(input_tx_id)

    with pytest.raises(TransactionFailed):
        testlang.root_chain.challengeInFlightExitNotCanonical(spend_tx.encoded, 0, unrelated_spend_tx.encoded, 0,
                                                              unrelated_spend_id, proof, signature,
                                                              input_tx.encoded, input_tx_id,
                                                              **{'from': owner_2.address})


def test_challenge_in_flight_exit_not_canonical_wrong_index_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                          force_invalid=True)
    spend_tx = testlang.child_chain.get_transaction(spend_id)
    double_spend_tx = testlang.child_chain.get_transaction(double_spend_id)

    testlang.start_in_flight_exit(spend_id)

    proof = testlang.get_merkle_proof(double_spend_id)
    signature = double_spend_tx.signatures[0]

    input_tx = testlang.child_chain.get_transaction(deposit_id)

    with pytest.raises(TransactionFailed):
        testlang.root_chain.challengeInFlightExitNotCanonical(spend_tx.encoded, 0, double_spend_tx.encoded, 1,
                                                              double_spend_id, proof, signature,
                                                              input_tx.encoded, deposit_id,
                                                              **{'from': owner_2.address})


def test_challenge_in_flight_exit_not_canonical_invalid_signature_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_2], [(owner_1.address, NULL_ADDRESS, 100)],
                                          force_invalid=True)

    testlang.start_in_flight_exit(spend_id)

    with pytest.raises(TransactionFailed):
        testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id, account=owner_2)


def test_challenge_in_flight_exit_not_canonical_invalid_proof_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                          force_invalid=True)
    spend_tx = testlang.child_chain.get_transaction(spend_id)
    double_spend_tx = testlang.child_chain.get_transaction(double_spend_id)

    testlang.start_in_flight_exit(spend_id)

    proof = b''
    signature = double_spend_tx.signatures[0]

    deposit_tx = testlang.child_chain.get_transaction(deposit_id)

    with pytest.raises(TransactionFailed):
        testlang.root_chain.challengeInFlightExitNotCanonical(spend_tx.encoded, 0, double_spend_tx.encoded, 0,
                                                              double_spend_id, proof, signature,
                                                              deposit_tx.encoded, deposit_id,
                                                              **{'from': owner_2.address})


def test_challenge_in_flight_exit_not_canonical_same_tx_twice_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                          force_invalid=True)

    testlang.start_in_flight_exit(spend_id)

    testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id, account=owner_2)

    with pytest.raises(TransactionFailed):
        testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id, account=owner_2)


def test_challenge_in_flight_exit_twice_older_position_should_succeed(testlang):
    owner_1, owner_2, owner_3, amount = testlang.accounts[0], testlang.accounts[1], testlang.accounts[2], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id_1 = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                            force_invalid=True)
    double_spend_id_2 = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 50)],
                                            force_invalid=True)

    testlang.start_in_flight_exit(spend_id)

    testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id_2, account=owner_2)
    testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id_1, account=owner_3)

    in_flight_exit = testlang.get_in_flight_exit(spend_id)
    assert in_flight_exit.bond_owner == owner_3.address
    assert in_flight_exit.oldest_competitor == double_spend_id_1
    assert not in_flight_exit.is_canonical


def test_challenge_in_flight_exit_twice_younger_position_should_fail(testlang):
    owner_1, owner_2, amount = testlang.accounts[0], testlang.accounts[1], 100
    deposit_id = testlang.deposit(owner_1, amount)
    spend_id = testlang.spend_utxo([deposit_id], [owner_1], [(owner_2.address, NULL_ADDRESS, 100)])
    double_spend_id_1 = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 100)],
                                            force_invalid=True)
    double_spend_id_2 = testlang.spend_utxo([deposit_id], [owner_1], [(owner_1.address, NULL_ADDRESS, 50)],
                                            force_invalid=True)

    testlang.start_in_flight_exit(spend_id)

    testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id_1, account=owner_2)

    with pytest.raises(TransactionFailed):
        testlang.challenge_in_flight_exit_not_canonical(spend_id, double_spend_id_2, account=owner_2)
