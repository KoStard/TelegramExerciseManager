from main.command_handlers import send_problem, answer_problem


def cycle(worker):
    if worker.command_argv:
        worker.answer_to_the_message("Cycle command can't get any arguments.")
        return
    answer_problem.answer_problem(worker)
    send_problem.send_problem(worker)
