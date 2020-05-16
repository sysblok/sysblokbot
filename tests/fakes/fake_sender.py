class FakeTelegramSender:
    def send_to_managers(self, *args, **kwargs):
        pass

    def create_chat_ids_send(self, *args, **kwargs):
        pass

    def create_reply_send(self, *args, **kwargs):
        return args
