from dataclasses import dataclass


@dataclass
class Interface:
    """Store the interface name and MAC address."""

    name: str
    mac: str | None


class Interfaces:
    """Store a mapping of interface names to their MAC addresses."""

    _FROM_MAC: dict[str, Interface] = {}
    _FROM_NAME: dict[str, Interface] = {}

    @classmethod
    def _reload(cls) -> None:
        """Update the data with any new network interfaces."""
        import psutil
        for interface_name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:  # Identifies MAC address family
                    cls._register(interface_name, addr.address)
                    break
            else:
                cls._register(interface_name, None)

    @classmethod
    def _register(cls, name: str, mac: str | None) -> Interface:
        """Register a MAC address."""
        interface = Interface(name, mac)
        cls._FROM_NAME[name] = interface
        if mac is not None:
            cls._FROM_MAC[mac] = interface
        return interface

    @classmethod
    def get_from_name(cls, name: str) -> Interface:
        """Get an interface from its name."""
        if name not in cls._FROM_NAME:
            cls._reload()
        try:
            return cls._FROM_NAME[name]
        except KeyError:
            return Interface(name, None)

    @classmethod
    def get_from_mac(cls, mac: str) -> Interface:
        """Get an interface from its MAC address."""
        if mac not in cls._FROM_MAC:
            cls._reload()
        try:
            return cls._FROM_MAC[mac]
        except KeyError:
            return Interface('', mac)
