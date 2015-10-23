import collections
import time
from coapthon import defines


class ObserveItem(object):
    def __init__(self, timestamp, non_counter, allowed, transaction):
        self.timestamp = timestamp
        self.non_counter = non_counter
        self.allowed = allowed
        self.transaction = transaction


class ObserveLayer(object):
    def __init__(self):
        self._relations = {}

    def send_request(self, request):
        """

        :type request: Request
        :param request:
        """
        return request

    def receive_response(self, response, transaction):
        """

        :type response: Response
        :param response:
        :type transaction: Transaction
        :param transaction:
        :rtype : Transaction
        """
        raise NotImplementedError

    def send_empty(self, transaction, message):
        """

        :type transaction: Transaction
        :param transaction:
        :type message: Message
        :param message:
        """
        pass

    def receive_request(self, transaction):
        """

        :type transaction: Transaction
        :param transaction:
        :rtype : Transaction
        """
        if transaction.request.observe == 0:
            # Observe request
            host, port = transaction.request.source
            key_token = hash(str(host) + str(port) + str(transaction.request.token))
            non_counter = 0
            if key_token in self._relations:
                # Renew registration
                allowed = True
            else:
                allowed = False
            self._relations[key_token] = ObserveItem(time.time(), non_counter, allowed, transaction)

        return transaction

    def receive_empty(self, empty, transaction):
        """

        :type empty: Message
        :param empty:
        :type transaction: Transaction
        :param transaction:
        :rtype : Transaction
        """
        if empty.type == defines.Types["RST"]:
            host, port = transaction.request.source
            key_token = hash(str(host) + str(port) + str(transaction.request.token))
            del self._relations[key_token]
            transaction.completed = True

    def send_response(self, transaction):
        """

        :type transaction: Transaction
        :param transaction:
        """
        host, port = transaction.request.source
        key_token = hash(str(host) + str(port) + str(transaction.request.token))
        if key_token in self._relations:
            if transaction.response.code == defines.Codes.CONTENT.number:
                if transaction.resource is not None and transaction.resource.observable:

                    transaction.response.observe = transaction.resource.observe_count
                    self._relations[key_token].allowed = True
                    self._relations[key_token].transaction = transaction
                    self._relations[key_token].timestamp = time.time()
                else:
                    del self._relations[key_token]
            elif transaction.response.code >= defines.Codes.ERROR_LOWER_BOUND:
                del self._relations[key_token]
        return transaction

    def notify(self, resource):
        ret = []
        for key in self._relations.keys():
            if self._relations[key].transaction.resource == resource:
                if self._relations[key].non_counter > defines.MAX_NON_NOTIFICATIONS \
                        or self._relations[key].transaction.request.type == defines.Types["CON"]:
                    self._relations[key].transaction.response.type = defines.Types["CON"]
                    self._relations[key].non_counter = 0
                elif self._relations[key].transaction.request.type == defines.Types["NON"]:
                    self._relations[key].non_counter += 1
                    self._relations[key].transaction.response.type = defines.Types["NON"]
                self._relations[key].transaction.resource = resource
                del self._relations[key].transaction.response.mid
                del self._relations[key].transaction.response.token
                ret.append(self._relations[key].transaction)
        return ret

