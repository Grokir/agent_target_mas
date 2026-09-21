import pytest

from agent_kernel.mesbroker import ACLMessage, InProcessBroker, Performative, UnknownRecipientError


@pytest.fixture
def broker():
    return InProcessBroker()


async def test_publish_then_receive_round_trip(broker):
    broker.register("agent-a")

    message = ACLMessage(
        sender="agent-b",
        receiver="agent-a",
        performative=Performative.REQUEST,
        content="task",
        conversation_id="thread-1",
    )
    await broker.publish(message)

    received = await broker.receive("agent-a")
    assert received is message


async def test_reply_to_defaults_to_sender(broker):
    message = ACLMessage(
        sender="agent-a",
        receiver="agent-b",
        performative=Performative.INFORM,
        content="result",
        conversation_id="thread-1",
    )
    assert message.reply_to == "agent-a"


async def test_reply_to_can_be_overridden(broker):
    message = ACLMessage(
        sender="agent-a",
        receiver="agent-b",
        performative=Performative.REQUEST,
        content="task",
        conversation_id="thread-1",
        reply_to="agent-a:one-shot-42",
    )
    assert message.reply_to == "agent-a:one-shot-42"


async def test_publish_to_unregistered_recipient_raises(broker):
    message = ACLMessage(
        sender="agent-a",
        receiver="ghost",
        performative=Performative.REQUEST,
        content="task",
        conversation_id="thread-1",
    )
    with pytest.raises(UnknownRecipientError):
        await broker.publish(message)


async def test_receive_on_unregistered_agent_raises(broker):
    with pytest.raises(UnknownRecipientError):
        await broker.receive("ghost")


async def test_unregister_removes_queue(broker):
    broker.register("agent-a")
    broker.unregister("agent-a")

    with pytest.raises(UnknownRecipientError):
        await broker.receive("agent-a")


async def test_messages_are_delivered_in_order(broker):
    broker.register("agent-a")

    for i in range(3):
        await broker.publish(ACLMessage(
            sender="agent-b",
            receiver="agent-a",
            performative=Performative.INFORM,
            content=i,
            conversation_id="thread-1",
        ))

    received = [(await broker.receive("agent-a")).content for _ in range(3)]
    assert received == [0, 1, 2]
