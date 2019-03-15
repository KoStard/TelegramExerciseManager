"""
Will handle text (not command) from participant group member in participant group
"""

from main.message_handlers import user_pg_pgm_answer_handler


def handle_pgm_text(worker):
    """
    Will handle text from participant_group message
    """
    if not worker['text']:
        return  # There is no text in the message
    if len(worker['text']) == 1 and worker.participant_group.activeProblem and (
            (not worker.participant_group.activeProblem.variants and worker['text'].upper() in (
                    'A', 'B', 'C', 'D', 'E')) or (
                    worker.participant_group.activeProblem.variants and worker.text.lower() in worker.participant_group.activeProblem.variants_dict.keys())):
        worker.source.variant = worker['text'].upper()
        user_pg_pgm_answer_handler.handle_answer(worker)
    else:
        pass  # Just regular message in participant group
