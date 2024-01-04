import numpy as np
from gnuradio import gr
from gnuradio import blocks
import osmosdr
import time
from queue import Empty, SimpleQueue
from pcdr.helpers import SimpleQueueTypeWrapped, queue_to_list
from typing import List, Optional
from typeguard import typechecked



class queue_source(gr.sync_block):
    ## TODO: Is this used anywhere? Let's start using Blk_queue_source instead

    def __init__(self, external_queue: SimpleQueueTypeWrapped, chunk_size: int, out_type = np.complex64):
        assert external_queue.qtype == np.ndarray
        assert external_queue.dtype == out_type
        assert external_queue.chunk_size == chunk_size
        gr.sync_block.__init__(
            self,
            name='Python Block: Queue Source',
            in_sig=[],
            out_sig=[(out_type, chunk_size)]
        )
        self.__queue = external_queue
        self.__chunk_size = chunk_size


    def work(self, input_items, output_items):
        try:
            output_items[0][0][:] = self.__queue.get_nowait()
            return 1
        except Empty:
            return -1  # Block is done
    
    
    def queue_put(self, data):
        assert len(data) == self.__chunk_size
        self.__queue.put(data)


class Blk_queue_source(gr.sync_block):
    @typechecked
    def __init__(self, dtype: type, chunk_size: int, timeout: Optional[float] = None):
        gr.sync_block.__init__(self,
            name='Python Block: Queue Source',
            in_sig=[],
            out_sig=[(dtype, chunk_size)]
        )
        self.queue = SimpleQueue()
        self.timeout = timeout

    def work(self, input_items, output_items):
        try:
            output_items[0][0][:] = self.queue.get(timeout=self.timeout)
            return 1
        except Empty:
            print("Queue is empty, block will now report 'done' to GNU Radio flowgraph")
            return -1


class Blk_sink_print(gr.sync_block):
    def __init__(self, sleep_seconds: float = 1e-6, only_print_1_in: int = 1, dtype: type = np.float32):
        gr.sync_block.__init__(self, name='Print sink', in_sig=[dtype], out_sig=[])
        self.only_print_1_in = only_print_1_in
        self.count = 0
        self.sleep_seconds = sleep_seconds

    def work(self, input_items, output_items):
        if self.count == 0:
            print(input_items[0][0])
            time.sleep(self.sleep_seconds)
        self.count = (self.count + 1) % self.only_print_1_in
        return 1


print_sink = Blk_sink_print  # Temporary alias while migrating to new name

class string_file_sink(gr.sync_block):

    def __init__(self, filename):
        gr.sync_block.__init__(
            self,
            name="Python Block: String File Sink",
            in_sig=[np.complex64],
            out_sig=[]
        )
        self.f = open(filename, "w")
        
    def work(self, input_items, output_items):
        singleDataPoint = input_items[0][0]

        self.f.write(f"{singleDataPoint}, ")
        self.f.flush()

        return 1


class queue_sink(gr.sync_block):
    ## TODO: Is this used anywhere? Let's start using Blk_queue_sink instead
    def __init__(self, chunk_size: int):
        gr.sync_block.__init__(
            self,
            name='Python Block: Data Queue Sink',
            in_sig=[(np.complex64, chunk_size)],
            out_sig=[]
        )
        self.__queue = SimpleQueueTypeWrapped(np.ndarray, np.complex64, chunk_size)
        self.__chunk_size = chunk_size


    def work(self, input_items, output_items):
        datacopy = input_items[0][0].copy()
        self.__queue.put(datacopy)
        return 1


    def get(self) -> np.ndarray:
        """Get a chunk from the queue of accumulated received data."""
        result = self.__queue.get()
        assert len(result) == self.__chunk_size
        return result

    def get_all(self) -> List[np.ndarray]:
        """Warning: this may or may not work while the flowgraph is running."""
        return queue_to_list(self.__queue)



class Blk_queue_sink(gr.sync_block):
    @typechecked
    def __init__(self, dtype: type, chunk_size: int):
        gr.sync_block.__init__(
            self,
            name='Python Block: Queue Sink',
            in_sig=[(dtype, chunk_size)],
            out_sig=[]
        )
        self.queue = SimpleQueue()

    def work(self, input_items, output_items):  
        datacopy = input_items[0][0].copy()
        self.queue.put(datacopy)
        return 1
