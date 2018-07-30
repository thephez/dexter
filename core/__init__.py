from __future__ import (absolute_import, division, print_function, with_statement)

import logging
import time

# The log used by all of the system
LOG = logging

# ------------------------------------------------------------------------------

class Component(object):
    '''
    A part of the system.
    '''
    def __init__(self, notifier):
        super(Component, self).__init__()
        self._notifier = notifier


    def start(self):
        '''
        Start this component going.
        '''
        pass


    def stop(self):
        '''
        Stop this component.
        '''
        pass


    def _notify(self, status):
        '''
        Notify of a status change.
        '''
        if self._notifier is not None:
            self._notifier.update_status(self, status)


    def __str__(self):
        return type(self).__name__


class Notifier(object):
    '''
    How a Component tells the system about its status changes.
    '''
    class _Status(object):
        def __init__(self, name):
            self._name = name

        def __str__(self):
            return self._name

    INIT    = _Status("<INITIALISING>")
    IDLE    = _Status("<IDLE>")
    ACTIVE  = _Status("<ACTIVE>")
    WORKING = _Status("<WORKING>")
    
    def update_status(self, component, status):
        '''
        Tell the system of a status change for a component.
        '''
        # Subclasses should implement this
        raise NotImplementedError("Abstract method called")

# ------------------------------------------------------------------------------

class Dexter(object):
    '''
    The main class which drives the system.
    '''
    class _MainNotifier(Notifier):
        '''
        Tell the system overall that we're busy.
        '''

        def update_status(self, component, status):
            '''
            @see L{Notifier.update_status()}
            '''
            LOG.info("Component %s is now %s",
                     component, status)


    @staticmethod
    def _get_component(full_classname, kwargs, notifier):
        '''
        The the instance of the given L{Component}.
    
        @type  full_classname: str
        @param full_classname:
            The fully qualified classname, e.g. 'dexter,input.AnInput'
        @type  kwargs: dict
        @param kwargs:
            The keyword arguments to use when calling the constructor.
        @type  notifier: L{Notifier}
        @param notifier:
            The notifier for the L{Component}.
        '''
        try:
            (module, classname) = full_classname.rsplit('.', 1)
            exec ('from %s import %s'  % (module, classname,))
            exec ('klass = %s'         % (        classname,))
            if kwargs is None:
                return klass(notifier)
            else:
                return klass(notifier, **kwargs)

        except Exception as e:
            raise ValueError("Failed to load component %s with kwargs %s: %s" %
                             (full_classname, kwargs, e))


    @staticmethod
    def _to_letters(word):
        '''
        Remove non-letters from a word.
        '''
        return ''.join(char 
                       for char in word
                       if 'a' <= char.lower() <= 'z')
        

    @staticmethod
    def _parse_key_phrase(phrase):
        '''
        Turn a string into a tuple, without punctuation, as lowercase.

        @type  phrase: str
        @param phrase:
            The key-phrase to sanitise.
        '''
        result = []
        for word in phrase.split(' '):
            # Strip to non-letters and only append if it's not the empty string
            word = Dexter._to_letters(word)
            if word != '':
                result.append(word.lower())

        # Safe to append
        return tuple(result)


    @staticmethod
    def _list_index(list, sublist, start=0):
        '''
        Find the index of of a sublist in a list.

        @type  list: list
        @param list:
            The list to look in.
        @type  sublist: list
        @param sublist:
            The list to look for.
        @type  start: int
        @param start:
            Where to start looking in the C{list}.
        '''
        # The empty list can't be in anything
        if len(sublist) == 0:
            raise ValuError("Empty sublist not in list")

        # Simple case
        if len(sublist) == 1:
            return list.index(sublist[0], start)

        # Okay, we have multiple elements in our sublist. Look for the first
        # one, and see that it's adjacent to the rest of the list. We 
        offset = start
        while True:
            try:
                first = Dexter._list_index(list, sublist[ :1], offset)
                rest  = Dexter._list_index(list, sublist[1: ], first + 1)
                if first + 1 == rest:
                    return first

            except ValueError:
                raise ValueError('%s not in %s' % (sublist, list))

            # Move the offset to be after the first instance of sublist[0], so
            # that we may find the next one, if any
            offset = first + 1


    def __init__(self, config):
        '''
        @type  config: configuration
        @param config:
            The configuration for the system.
        '''
        # Set up the key-phrases, sanitising them
        self._key_phrases = tuple(Dexter._parse_key_phrase(p)
                                  for p in config['key_phrases'])

        # Create the components, using our notifier
        self._notifier = Dexter._MainNotifier()
        components = config.get('components', {})
        self._inputs = [
            Dexter._get_component(classname, kwargs, self._notifier)
            for (classname, kwargs) in components.get('inputs', [])
        ]
        self._outputs = [
            Dexter._get_component(classname, kwargs, self._notifier)
            for (classname, kwargs) in components.get('outputs', [])
        ]
        self._services = [
            Dexter._get_component(classname, kwargs, self._notifier)
            for (classname, kwargs) in components.get('services', [])
        ]

        # And we're off!
        self._running  = True


    def run(self):
        '''
        The main worker.
        '''
        LOG.info("Starting the system")
        self._start()

        LOG.info("Entering main loop")
        while self._running:
            try:
                # Loop over all the inputs and see if they have anything pending
                for input in self._inputs:
                    # Attempt a read, this will return None if there's nothing
                    # available
                    tokens = input.read()
                    if tokens is not None:
                        # Okay, we read something, attempt to handle it
                        LOG.info("Read from %s: %s" %
                                 (input, [str(t) for t in tokens]))
                        result = self._handle(tokens)

                        # If we got something back then give it back to the user
                        if result is not None:
                            self._respond(result)

                # Wait for a bit before going around again
                time.sleep(0.1)

            except KeyboardInterrupt:
                LOG.warning("KeyboardInterrupt received")
                break

        # We're out of the main loop, shut things down
        LOG.info("Stopping the system")
        self._stop()


    def _start(self):
        '''
        Start the system going.
        '''
        for component in self._inputs + self._outputs + self._services:
            # If these throw then it's fatal
            LOG.info("Starting %s" % (component,))
            component.start()


    def _stop(self):
        '''
        Stop the system.
        '''
        for component in self._inputs + self._outputs + self._services:
            # Best effort, since we're likely shutting down
            try:
                LOG.info("Stopping %s" % (component,))
                component.stop()

            except Exception as e:
                LOG.error("Failed to stop %s: %$s" % (component, e))


    def _handle(self, tokens):
        '''
        Handle a list of L{Token}s from the input.

        @type  tokens: list(L{Token})
        @param tokens:
            The tokens to handle.

        @rtype: str
        @return:
            The textual response, if any.
        '''
        # Give back nothing if we have no tokens
        if tokens is None:
            return None

        # See if the key-phrase is in the tokens and use it to determine the
        # offset of the command.
        words = [Dexter._to_letters(token.element).lower()
                 for token in tokens]
        offset = None
        for key_phrase in self._key_phrases:
            try:
                offset = (Dexter._list_index(words, key_phrase) +
                          len(key_phrase))
            except ValueError:
                pass

        # If we have an offset then we found a key-phrase
        if offset is None:
            LOG.info("Key pharses %s not found in %s" %
                     (self._key_phrases, words))
            return None

        # See which services want them
        handlers = []
        for service in self._services:
            handler = service.evaluate(tokens[offset:])
            if handler is not None:
                handlers.append(handler)

        # Anything?
        if len(handlers) == 0:
            return "I'm sorry, I don't know how to help with that"

        # Okay, put the handlers into order of belief and try them. Notice that
        # we want the higher beliefs first so we flip the pair in the cmp call.
        handlers = sorted(handlers, cmp=lambda a, b: cmp(b.belief, a.belief))

        # Now try each of the handlers
        response = ''
        error    = False
        for handler in handlers:
            try:
                # Invoked the handler and see what we get back
                result = handler.handle()
                if result is None:
                    continue

                # Accumulate into the resultant text
                if result.text is not None:
                    response += result.text

                # Stop here?
                if result.is_exclusive:
                    break
                
            except Exception as e:
                error = True
                LOG.error(
                    "Handler %s with tokens %s for service %s yielded: %s" %
                    (handler, handler.tokens, handler.service, e)
                )

        # Give back whatever we had, if anything
        if len(response) > 0:
            return response
        else:
            return None


    def _respond(self, response):
        '''
        Given back the response to the user via the outputs.

        @type  response: str
        @param response:
            The text to send off to the user in the real world.
        '''
        # Give back nothing if we have no response
        if response is None:
            return None

        # Simply hand it to all the outputs
        for output in self._outputs:
            try:
                output.write(response)
            except Exception as e:
                LOG.error("Failed to respond with %s: %s" % (output, e))
        
