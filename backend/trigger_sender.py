from time import sleep

from abc import ABC, abstractmethod

from pyftdi.ftdi import Ftdi
from pyftdi.gpio import GpioAsyncController
from pylsl import StreamInfo, StreamOutlet, resolve_streams


from backend.triggers import triggers

class TriggerSender(ABC):
    @abstractmethod
    def sendTrigger(self, trigger: int):
        pass


class TriggerSenderImpl(TriggerSender):
    gpio1out: GpioAsyncController | None = None
    gpio2out: GpioAsyncController | None = None
    lsl_outlet: StreamOutlet | None = None

    def __init__(
        self,
        gpio1: bool = True,
        gpio2: bool = True,
        lsl: bool = True,
    ):
        if gpio1 or gpio2:
            # add the brainproducts Triggerbox to the known devices
            Ftdi.add_custom_vendor(0x1103, "Brainproducts")
            Ftdi.add_custom_product(0x1103, 0x0021)
        if gpio1:
            self.gpio1out = GpioAsyncController()
            # 0 is in, 1 is out
            self.gpio1out.configure(
                "ftdi://Brainproducts:0x0021:TB6UJGXU/1", direction=0b11111111
            )  # 1-8, all outputs, change TBYOOT0G/1 according to found devices
        if gpio2:
            self.gpio2out = GpioAsyncController()
            self.gpio2out.configure(
                "ftdi://Brainproducts:0x0021:TB6EUW95/1", direction=0b11111111
            )  # 1-8, all outputs, change TBYOOT0G/1 according to found devices
        if lsl:
            lsl_info = StreamInfo(name="target_trigger", source_id="ttID255")
            # resolve_stream()
            self.lsl_outlet = StreamOutlet(lsl_info)

        self.sendTrigger(triggers["STARTEDTRIGGERSENDER"])
        for x in range(3):
            sleep(1)
            self.sendTrigger(triggers["STARTEDTRIGGERSENDER_SEQBASE"] + x)

    def sendTrigger(self, trigger: int):
        if trigger < 0 or trigger > 255:
            raise ValueError("trigger value out of range")
        if self.gpio1out is not None:
            self.gpio1out.write(0)
        if self.gpio2out is not None:
            self.gpio2out.write(0)

        sleep(0.005)

        if self.gpio1out is not None:
            self.gpio1out.write(trigger)
        if self.gpio2out is not None:
            self.gpio2out.write(trigger)
        if self.lsl_outlet is not None:
            self.lsl_outlet.push_sample([trigger])

