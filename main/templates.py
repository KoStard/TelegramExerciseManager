message_removal_message_with_highest_role_template = \
    ("Dear {name}, your message will be removed, because {cause}.\n"
     "Your current highest role is \"{highest_role}\".")

command_rejection_message_template = (
    "Dear {name}, you don't have permission to use "
    "command \"{command}\" - your highest role is \"{highest_role}\"."
)
