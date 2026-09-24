class NullArchive:
    """No-op archive, used when Gmail write-back is not configured."""

    def archive(self, msg, thread_id=None):
        raise NotImplementedError

    enabled = False
