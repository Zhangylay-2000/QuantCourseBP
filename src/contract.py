from __future__ import annotations
from abc import ABC, abstractmethod

import numpy as np

from src.enums import *
from statistics import mean


class Contract(ABC):
    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float, num_mon: int = 1) -> None:
        self._underlying: Stock = und
        self._derivative_type: PutCallFwd = dtype
        self._derivative_longshort: LongShort = longshort
        self._ls = 1 if longshort == LongShort.LONG else -1
        self._strike: float = strk
        self._expiry: float = exp
        self._num_mon: int = num_mon    # Asian: nr of averaging points; Barrier: nr of monitoring points

        if self.__class__.__name__ != 'Contract':
            self._contract = self.__class__.__name__.replace('Contract', '')
        else:
            self._contract = None

    def get_contract(self) -> ContractType:
        return self._contract

    def get_und(self) -> Stock:
        return self._underlying

    def get_type(self) -> PutCallFwd:
        return self._derivative_type

    def get_longshort(self) -> LongShort:
        return self._derivative_longshort

    def get_strike(self) -> float:
        return self._strike

    def get_expiry(self) -> float:
        return self._expiry

    def __str__(self) -> str:
        return str(self.to_dict())

    @abstractmethod
    def to_dict(self) -> dict[str, any]:
        return {
            "contract": self._contract,
            "underlying": self._underlying,
            "type": self._derivative_type,
            "longshort": self._derivative_longshort,
            "strike": self._strike,
            "expiry": self._expiry
        }

    @abstractmethod
    def convert_to_generic(self) -> GenericContract:
        pass

    @abstractmethod
    def get_timeline(self) -> list[float]:
        pass

    def _raise_incorrect_derivative_type(self):
        raise TypeError(f'Derivative type of {type(self).__name__} must be CALL or PUT')

    def _raise_incorrect_derivative_type_generic(self):
        raise TypeError(f'Derivative type of {type(self).__name__} must be CALL, PUT or FWD')


class VanillaContract(Contract):
    def to_dict(self) -> dict[str, any]:
        return super().to_dict()

    @abstractmethod
    def convert_to_generic(self) -> GenericContract:
        pass

    @abstractmethod
    def payoff(self, spot: float) -> float:
        pass

    def get_timeline(self) -> list[float]:
        return [self._expiry]


class ForwardContract(VanillaContract):
    def __init__(self, und: Stock, longshort: LongShort, strk: float, exp: float) -> None:
        super().__init__(und, PutCallFwd.FWD, longshort, strk, exp)


    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry)

    def payoff(self, spot: float) -> float:
        return self._ls * (spot - self._strike)


class EuropeanContract(VanillaContract):

    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT]:
            self._raise_incorrect_derivative_type()
        super().__init__(und, dtype, longshort, strk, exp)

    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry)

    def payoff(self, spot: float) -> float:
        if self._derivative_type == PutCallFwd.CALL:
            return self._ls * max(spot - self._strike, 0)
        elif self._derivative_type == PutCallFwd.PUT:
            return self._ls * max(self._strike - spot, 0)
        else:
            self._raise_incorrect_derivative_type()


class AmericanContract(VanillaContract):

    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT]:
            self._raise_incorrect_derivative_type()
        super().__init__(und, dtype, longshort, strk, exp)

    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry)

    def payoff(self, spot: float) -> float:
        if self._derivative_type == PutCallFwd.CALL:
            return self._ls * max(spot - self._strike, 0)
        elif self._derivative_type == PutCallFwd.PUT:
            return self._ls * max(self._strike - spot, 0)
        else:
            self._raise_incorrect_derivative_type()


class EuropeanDigitalContract(VanillaContract):

    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT]:
            self._raise_incorrect_derivative_type()
        super().__init__(und, dtype, longshort, strk, exp)

    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry)

    def payoff(self, spot: float) -> float:
        if self._derivative_type == PutCallFwd.CALL:
            return self._ls * float(spot - self._strike > 0)
        elif self._derivative_type == PutCallFwd.PUT:
            return self._ls * float(self._strike - spot > 0)
        else:
            self._raise_incorrect_derivative_type()


class ExoticContract(Contract):

    def to_dict(self) -> dict[str, any]:
        return super().to_dict()

    @abstractmethod
    def convert_to_generic(self) -> GenericContract:
        pass

    @abstractmethod
    def payoff(self, spot: float) -> float:
        pass

    def get_timeline(self) -> list[float]:
        return [((i+1)/self._num_mon)*self._expiry for i in range(self._num_mon)]

    def _raise_incorrect_barrier_updown_type(self):
        raise TypeError(f'Updown parameter of {type(self).__name__} must be UP or DOWN')

    def _raise_incorrect_barrier_inout_type(self):
        raise TypeError(f'Inout parameter of {type(self).__name__} must be IN or OUT')


class AsianContract(ExoticContract):

    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT]:
            self._raise_incorrect_derivative_type()
        super().__init__(und, dtype, longshort, strk, exp)

    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry)

    def payoff(self, prices_und: float) -> float:
    # TO DO: prices_und to derive from the underlying process using the timeline
        if self._derivative_type == PutCallFwd.CALL:
            return self._ls * max(mean(prices_und) - self._strike, 0)
        elif self._derivative_type == PutCallFwd.PUT:
            return self._ls * max(self._strike - mean(prices_und), 0)
        else:
            self._raise_incorrect_derivative_type()


class EuropeanBarrierContract(ExoticContract):

    def __init__(self, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float,
                 barrier: float, updown: UpDown, inout: InOut) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT]:
            self._raise_incorrect_derivative_type()
        if updown not in [UpDown.UP, UpDown.DOWN]:
            self._raise_incorrect_barrier_updown_type()
        if inout not in [InOut.IN, InOut.OUT]:
            self._raise_incorrect_barrier_inout_type()
        super().__init__(und, dtype, longshort, strk, exp)
        self._barrier = barrier
        self._updown = updown
        self._inout = inout

    def get_barrier(self) -> float:
        return self._barrier

    def get_updown(self) -> UpDown:
        return self._updown

    def get_inout(self) -> InOut:
        return self._inout

    def is_breached(self, prices_und) -> bool:
        if self._updown == 'UP':
            return( any(self._barrier <= price for price in prices_und) )
        else:
            return (any(self._barrier >= price for price in prices_und) )

    def convert_to_generic(self) -> GenericContract:
        return GenericContract(self._contract, self._underlying, self._derivative_type,
                               self._derivative_longshort, self._strike, self._expiry,
                               self._barrier, self._updown, self._inout)

    def to_dict(self) -> dict[str, any]:
        out = super().to_dict()
        out |= {"barrier": self._barrier, "updown": self._updown, "inout": self._inout}
        return out

    def payoff(self, prices_und: float) -> float:
    # TO DO: prices_und to derive from the underlying process using the timeline

        mult = (self._inout == 'IN') * self.is_breached(prices_und) + \
               (self._inout == 'OUT') * (1 - self.is_breached(prices_und))

        if self._derivative_type == PutCallFwd.CALL:
            return mult * self._ls * max(prices_und[-1] - self._strike, 0)
        elif self._derivative_type == PutCallFwd.PUT:
            return mult * self._ls * max(self._strike - prices_und[-1], 0)
        else:
            self._raise_incorrect_derivative_type()


class GenericContract(ExoticContract):

    def __init__(self, contract: ContractType, und: Stock, dtype: PutCallFwd, longshort: LongShort, strk: float, exp: float,
                 barrier: float = np.Inf, updown: UpDown = None, inout: InOut = None) -> None:
        if dtype not in [PutCallFwd.CALL, PutCallFwd.PUT, PutCallFwd.FWD]:
            self._raise_incorrect_derivative_type_generic()
        if updown not in [UpDown.UP, UpDown.DOWN, None]:
            self._raise_incorrect_barrier_updown_type()
        if inout not in [InOut.IN, InOut.OUT, None]:
            self._raise_incorrect_barrier_inout_type()
        super().__init__(und, dtype, longshort, strk, exp)
        self._contract = contract
        self._barrier = barrier
        self._updown = updown
        self._inout = inout

    def get_contract_type(self) -> ContractType:
        return self._contract

    def get_barrier(self) -> float:
        return self._barrier

    def get_updown(self) -> UpDown:
        return self._updown

    def get_inout(self) -> InOut:
        return self._inout

    def is_breached(self, prices_und) -> bool:
        if self._updown == 'UP':
            return( any([self._barrier <= price for price in prices_und]) )
        else:
            return (any([self._barrier >= price for price in prices_und]))

    def to_dict(self) -> dict[str, any]:
        out = super().to_dict()
        out |= {"barrier": self._barrier, "updown": self._updown, "inout": self._inout}
        return out

    def convert_to_generic(self) -> GenericContract:
        return self

    def payoff(self, prices_und: float) -> float:
    # TO DO: prices_und to derive from the underlying process using the timeline

        if self._contract == ContractType.FORWARD:
            return self._ls * (prices_und - self._strike)

        elif self._contract == ContractType.AMERICANOPTION or self._contract == ContractType.EUROPEANOPTION:
            if self._derivative_type == PutCallFwd.CALL:
                return self._ls * max(prices_und - self._strike, 0)
            elif self._derivative_type == PutCallFwd.PUT:
                return self._ls * max(self._strike - prices_und, 0)

        elif self._contract == ContractType.EUROPEANDIGITALOPTION:
            if self._derivative_type == PutCallFwd.CALL:
                return self._ls * float(prices_und - self._strike > 0)
            elif self._derivative_type == PutCallFwd.PUT:
                return self._ls * float(self._strike - prices_und > 0)

        elif self._contract == ContractType.ASIANOPTION:
            if self._derivative_type == PutCallFwd.CALL:
                return self._ls * max(mean(prices_und) - self._strike, 0)
            elif self._derivative_type == PutCallFwd.PUT:
                return self._ls * max(self._strike - mean(prices_und), 0)

        elif self._contract == ContractType.EUROPEANBARRIEROPTION:
            mult = (self._inout == 'IN') * self.is_breached(prices_und) + \
                   (self._inout == 'OUT') * (1 - self.is_breached(prices_und))
            if self._derivative_type == PutCallFwd.CALL:
                return mult * self._ls * max(prices_und[-1] - self._strike, 0)
            elif self._derivative_type == PutCallFwd.PUT:
                return mult * self._ls * max(self._strike - prices_und[-1], 0)


def main():

    values = [-1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3]

    trade1 = ForwardContract('Apple', 'SHORT', 1, 2)
    print(trade1)
    print([trade1.payoff(value) for value in values])
    print(trade1.get_contract())

    generic_trade1 = trade1.convert_to_generic()
    print(generic_trade1)
    print([generic_trade1.payoff(value) for value in values])

    trade2 = EuropeanContract('OTP', 'CALL', 'LONG', 1, 2)
    print(trade2)
    print([trade2.payoff(value) for value in values])
    generic_trade2 = trade2.convert_to_generic()
    print(generic_trade2)
    print([generic_trade2.payoff(value) for value in values])

    trade3 = AmericanContract('Tesla', 'CALL', 'LONG', 1, 2)
    print(trade3)
    print([trade3.payoff(value) for value in values])
    generic_trade3 = trade3.convert_to_generic()
    print(generic_trade3)
    print([generic_trade3.payoff(value) for value in values])

    trade4 = EuropeanDigitalContract('Mol', 'CALL', 'LONG', 1, 2)
    print(trade4)
    print([trade4.payoff(value) for value in values])
    generic_trade4 = trade4.convert_to_generic()
    print(generic_trade4)
    print([generic_trade4.payoff(value) for value in values])

    trade5 = AsianContract('Microsoft', 'CALL', 'LONG', 0.8, 2)
    print(trade5)
    print(trade5.payoff(values))
    generic_trade5 = trade5.convert_to_generic()
    print(generic_trade5)
    print(generic_trade5.payoff(values))

    trade6 = EuropeanBarrierContract('Deutshe Bank', 'CALL', 'LONG', 1.5, 2, 2.7, "UP", "IN")
    print(trade6)
    print(trade6.is_breached([1, 2, 2.5, 2]),
          trade6.is_breached([1, 2, 3.5, 2]) )
    print(trade6.payoff(values))
    generic_trade6 = trade6.convert_to_generic()
    print(generic_trade6)
    print(generic_trade6.is_breached([1, 2, 2.5, 2]),
          generic_trade6.is_breached([1, 2, 3.5, 2]) )
    print(generic_trade6.payoff(values))



if __name__ == '__main__': main()

