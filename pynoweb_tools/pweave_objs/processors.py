from __future__ import print_function

import sys
import re
import os

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import queue
except ImportError:
    import Queue as queue

import code

from tornado.gen import TimeoutError
from jupyter_client.blocking import BlockingKernelClient
from jupyter_client.manager import start_new_kernel

from pweave import PwebProcessor
# from pweave import subsnippets, config

from nbformat.v4 import output_from_msg
# from IPython.core import inputsplitter


class PwebIPythonExtProcessor(PwebProcessor):
    r""" A processor that runs code chunks in the current Ipython session.
    If there isn't one, then it creates one.
    """

    def __init__(self, parsed, source, mode, formatdict):
        super(PwebIPythonExtProcessor, self).__init__(
            parsed, source, mode, formatdict)

        import IPython

        self.IPy = IPython.get_ipython()
        if self.IPy is None:
            # TODO: `InteractiveShell` takes namespace dictionaries; perhaps
            # we can use this [approximately] reload sessions by taking
            # snapshots of `IPy.all_ns_refs` and/or just `IPy.user_ns` after
            # each chunk evaluation.  Then we might be able to "reload".
            # Checkout `IPy.displayhook.update_user_ns`, too.
            x = IPython.core.interactiveshell.InteractiveShell()
            self.IPy = x.get_ipython()

        self.prompt_count = 1

    def loadstring(self, code, **kwargs):
        r"""
        TODO: Considerusing `IPy.user_expressions`; it provides a nice map
        between multiple string-keyed lines and output.
        """
        tmp = StringIO()
        sys.stdout = tmp
        # compiled = compile(code, '<input>', 'exec')
        # exec compiled in PwebProcessorGlobals.globals
        self.IPy.run_cell(code)
        result = "\n" + tmp.getvalue()
        tmp.close()
        sys.stdout = self._stdout
        return result

    def loadterm(self, code_str, **kwargs):
        # Write output to a StringIO object
        # loop trough the code lines
        statement = ""
        prompt = "In [%i]:" % self.prompt_count
        chunkresult = "\n"
        block = code_str.lstrip().splitlines()

        for x in block:
            chunkresult += ('\n%s %s\n' % (prompt, x))
            statement += x + '\n'

            # TODO: If all this is just to get formatted IPython input
            # then perhaps `IPy.history_manager.input_hist_parsed` is better.
            # Will need to add `store_history=True` to `IPy.run_cell` calls.

            # Is the statement complete?
            compiled_statement = code.compile_command(statement)
            if compiled_statement is None:
                # No, not yet.
                prompt = "..."
                continue

            if not prompt.startswith('In ['):
                chunkresult += ('%s \n' % prompt)

            tmp = StringIO()
            sys.stdout = tmp
            # return_value = eval(compiled_statement, PwebProcessorGlobals.globals)
            self.IPy.run_code(compiled_statement)
            result = tmp.getvalue()
            # if return_value is not None:
            #     result += repr(return_value)
            tmp.close()
            sys.stdout = self._stdout
            if result:
                chunkresult += ("Out[{}]: {}".format(self.prompt_count,
                                                     result.rstrip()))

            statement = ""
            self.prompt_count += 1
            prompt = 'In [%i]:' % self.prompt_count

        return chunkresult

    def loadinline(self, content):
        """Evaluate code from doc chunks using ERB markup"""
        # Flags don't work with ironpython
        splitted = re.split('(<%[\w\s\W]*?%>)', content)  # , flags = re.S)
        # No inline code
        if len(splitted) < 2:
            return content

        n = len(splitted)

        for i in range(n):
            elem = splitted[i]
            if not elem.startswith('<%'):
                continue
            if elem.startswith('<%='):
                code = elem.replace('<%=', '').replace('%>', '').lstrip()
                result = self.loadstring('print %s,' % code).replace(
                    '\n', '', 1)
                splitted[i] = result
                continue
            if elem.startswith('<%'):
                code = elem.replace('<%', '').replace('%>', '').lstrip()
                result = self.loadstring('%s' % code).replace('\n', '', 1)
                splitted[i] = result
        return ''.join(splitted)


class JupyterAwareProcessor(PwebProcessor):
    r""" This processor checks for existing Jupyter/IPython kernels
    in the currently running session.
    """

    def __init__(self, parsed, source, mode, formatdict, figdir, outdir,
                 kernel="python", timeout=None,
                 interrupt_on_timeout=True,
                 raise_on_iopub_timeout=True):
        super(JupyterAwareProcessor, self).__init__(parsed, source, mode,
                                                    formatdict, figdir,
                                                    outdir)

        self.extra_arguments = None
        self.timeout = timeout
        path = os.path.abspath(outdir)
        self.interrupt_on_timeout = interrupt_on_timeout
        self.raise_on_iopub_timeout = raise_on_iopub_timeout

        if 'IPython' in sys.modules:
            from IPython import get_ipython
            self.ip = get_ipython()
            if self.ip is not None:
                self.kernel = getattr(self.ip, 'kernel', False)
                self.km, self.kc = self.start_existing_kernel()

        if self.kc is None:
            self.km, self.kc = start_new_kernel(
                kernel_name=kernel,
                extra_arguments=self.extra_arguments,
                stderr=open(os.devnull, 'w'),
                cwd=path)
            # TODO: Get the kernel object from the kernel manager?
            self.kernel = None
            self.kc.allow_stdin = False

    def start_existing_kernel(self):
        connection_file = self.ip.config['IPKernelApp']['connection_file']

        kc = BlockingKernelClient(connection_file=connection_file)
        kc.load_connection_file()
        kc.start_channels()
        # kc.wait_for_ready(timeout=10)

        # Inspired by jupyter-run.
        # kc.hb_channel.unpause()
        # info_msg = kc.kernel_info()
        # info_reply = kc.get_shell_msg(timeout=1)

        # Useful: `kc.execute_interactive`?

        return None, kc

    def close(self):
        self.kc.stop_channels()
        if self.km is not None:
            self.km.shutdown_kernel(now=True)

    def run_cell_remote(self, src):
        r"""
        From: https://github.com/mrocklin/distributed/blob/master/distributed/_ipython_utils.py
        """

        msg_id = self.kc.execute(src.lstrip())

        if self.kernel:
            socket = self.ip.display_pub.pub_socket
            session = self.ip.display_pub.session
            parent_header = self.ip.display_pub.parent_header

        while True:
            try:
                msg = self.kc.get_iopub_msg(timeout=self.timeout)
            except queue.Empty:
                raise TimeoutError("Timeout waiting for IPython output")

            if msg['parent_header'].get('msg_id') != msg_id:
                continue
            msg_type = msg['header']['msg_type']
            content = msg['content']
            if msg_type == 'status':
                if content['execution_state'] == 'idle':
                    # idle means output is done
                    break
            elif msg_type == 'stream':
                import pdb; pdb.set_trace()  # XXX BREAKPOINT
                stream = getattr(sys, content['name'])
                stream.write(content['text'])
            elif msg_type in ('display_data', 'execute_result', 'error'):
                if self.kernel:
                    session.send(socket, msg_type, content,
                                 parent=parent_header)
                else:
                    if msg_type == 'error':
                        print('\n'.join(content['traceback']),
                              file=sys.stderr)
                    else:
                        sys.stdout.write(content['data'].get('text/plain', ''))
            else:
                pass

    def run_cell(self, src):
        cell = {}
        cell["source"] = src.lstrip()

        msg_id = self.kc.execute(src.lstrip())

        # wait for finish, with timeout
        while True:
            try:
                msg = self.kc.shell_channel.get_msg(timeout=self.timeout)
            except queue.Empty:
                if self.interrupt_on_timeout:
                    # self.log.error("Interrupting kernel")
                    if self.km is not None:
                        self.km.interrupt_kernel()
                    break
                else:
                    try:
                        exception = TimeoutError
                    except NameError:
                        exception = RuntimeError
                    raise exception(
                        "Cell execution timed out, see log for details.")

            if msg['parent_header'].get('msg_id') == msg_id:
                break
            else:
                continue

        outs = []

        while True:
            try:
                msg = self.kc.iopub_channel.get_msg(timeout=4)
            except queue.Empty:
                # self.log.warn("Timeout waiting for IOPub output")
                if self.raise_on_iopub_timeout:
                    raise RuntimeError("Timeout waiting for IOPub output")
                else:
                    break
            if msg['parent_header'].get('msg_id') != msg_id:
                continue

            msg_type = msg['msg_type']
            content = msg['content']

            # set the prompt number for the input and the output
            if 'execution_count' in content:
                cell['execution_count'] = content['execution_count']

            if msg_type == 'status':
                if content['execution_state'] == 'idle':
                    break
                else:
                    continue
            elif msg_type == 'execute_input':
                continue
            elif msg_type == 'clear_output':
                outs = []
                continue
            elif msg_type.startswith('comm'):
                continue

            try:
                out = output_from_msg(msg)
            except ValueError:
                self.log.error("unhandled iopub msg: " + msg_type)
            else:
                outs.append(out)

        return outs

    def loadstring(self, code_str, **kwargs):
        # return self.run_cell(code_str)
        return self.run_cell_remote(code_str)

    def loadterm(self, code_str, **kwargs):
        return((code_str, self.run_cell(code_str)))

    def load_inline_string(self, code_string):
        from nbconvert import filters
        outputs = self.loadstring(code_string)
        result = ""
        for out in outputs:
            if out["output_type"] == "stream":
                result += out["text"]
            elif out["output_type"] == "error":
                result += filters.strip_ansi("".join(out["traceback"]))
            elif "text/plain" in out["data"]:
                result += out["data"]["text/plain"]
            else:
                result = ""
        return result


# class IPythonProcessor(JupyterProcessor):
#     """Contains IPython specific functions"""

#     def __init__(self, *args):
#         super(IPythonProcessor, self).__init__(*args)
#         if config.rcParams["usematplotlib"]:
#             self.init_matplotlib()

#     def init_matplotlib(self):
#         self.loadstring(subsnippets.init_matplotlib)

#     def pre_run_hook(self, chunk):
#         f_size = """matplotlib.rcParams.update({"figure.figsize" : (%i, %i)})""" % chunk["f_size"]
#         f_dpi = """matplotlib.rcParams.update({"savefig.dpi" : %i})""" % chunk["dpi"]
#         self.loadstring("\n".join([f_size, f_dpi]))

#     def loadterm(self, code_str, **kwargs):
#         splitter = inputsplitter.IPythonInputSplitter()
#         code_lines = code_str.lstrip().splitlines()
#         sources = []
#         outputs = []

#         for line in code_lines:
#             if splitter.push_accepts_more():
#                 splitter.push_line(line)
#             else:
#                 code_str = splitter.source
#                 sources.append(code_str)
#                 out = self.loadstring(code_str)
#                 #print(out)
#                 outputs.append(out)
#                 splitter.reset()
#                 splitter.push_line(line)


#         if splitter.source != "":
#             code_str = splitter.source
#             sources.append(code_str)
#             out = self.loadstring(code_str)
#             outputs.append(out)

#         return((sources, outputs))
