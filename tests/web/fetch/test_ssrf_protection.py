"""Tests for SSRF (Server-Side Request Forgery) protection.

This module provides comprehensive tests for the SSRF protection mechanisms
in the URL fetcher, including:
- IPv4 private range blocking
- IPv6 private range blocking
- Loopback address blocking
- Link-local address blocking
- DNS resolution validation
- URL host extraction edge cases
- Malformed IP address handling
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from code_forge.web.fetch.fetcher import (
    BLOCKED_IP_RANGES,
    FetchError,
    is_private_ip,
    validate_url_host,
)


class TestIsPrivateIP:
    """Tests for the is_private_ip function."""

    # IPv4 Private Class A (10.0.0.0/8)
    @pytest.mark.parametrize(
        "ip",
        [
            "10.0.0.0",
            "10.0.0.1",
            "10.255.255.255",
            "10.100.50.25",
            "10.1.2.3",
        ],
    )
    def test_ipv4_private_class_a_blocked(self, ip: str) -> None:
        """Test that Class A private IPs (10.0.0.0/8) are blocked."""
        assert is_private_ip(ip) is True

    # IPv4 Private Class B (172.16.0.0/12)
    @pytest.mark.parametrize(
        "ip",
        [
            "172.16.0.0",
            "172.16.0.1",
            "172.31.255.255",
            "172.20.10.5",
            "172.17.0.1",  # Common Docker IP
        ],
    )
    def test_ipv4_private_class_b_blocked(self, ip: str) -> None:
        """Test that Class B private IPs (172.16.0.0/12) are blocked."""
        assert is_private_ip(ip) is True

    # IPv4 Private Class C (192.168.0.0/16)
    @pytest.mark.parametrize(
        "ip",
        [
            "192.168.0.0",
            "192.168.0.1",
            "192.168.1.1",
            "192.168.255.255",
            "192.168.100.50",
        ],
    )
    def test_ipv4_private_class_c_blocked(self, ip: str) -> None:
        """Test that Class C private IPs (192.168.0.0/16) are blocked."""
        assert is_private_ip(ip) is True

    # IPv4 Loopback (127.0.0.0/8)
    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.0",
            "127.0.0.1",
            "127.255.255.255",
            "127.0.0.2",
            "127.1.2.3",
        ],
    )
    def test_ipv4_loopback_blocked(self, ip: str) -> None:
        """Test that loopback IPs (127.0.0.0/8) are blocked."""
        assert is_private_ip(ip) is True

    # IPv4 Link-local (169.254.0.0/16) - AWS metadata, etc.
    @pytest.mark.parametrize(
        "ip",
        [
            "169.254.0.0",
            "169.254.0.1",
            "169.254.169.254",  # AWS metadata endpoint
            "169.254.255.255",
            "169.254.100.100",
        ],
    )
    def test_ipv4_link_local_blocked(self, ip: str) -> None:
        """Test that link-local IPs (169.254.0.0/16) are blocked."""
        assert is_private_ip(ip) is True

    # IPv6 Loopback (::1/128)
    @pytest.mark.parametrize(
        "ip",
        [
            "::1",
            "0:0:0:0:0:0:0:1",
        ],
    )
    def test_ipv6_loopback_blocked(self, ip: str) -> None:
        """Test that IPv6 loopback (::1) is blocked."""
        assert is_private_ip(ip) is True

    # IPv6 Private (fc00::/7 - includes fc00::/8 and fd00::/8)
    @pytest.mark.parametrize(
        "ip",
        [
            "fc00::1",
            "fc00::",
            "fd00::1",
            "fd12:3456:789a::1",
            "fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        ],
    )
    def test_ipv6_private_blocked(self, ip: str) -> None:
        """Test that IPv6 private addresses (fc00::/7) are blocked."""
        assert is_private_ip(ip) is True

    # IPv6 Link-local (fe80::/10)
    @pytest.mark.parametrize(
        "ip",
        [
            "fe80::1",
            "fe80::",
            "fe80::1:2:3:4",
            "febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        ],
    )
    def test_ipv6_link_local_blocked(self, ip: str) -> None:
        """Test that IPv6 link-local addresses (fe80::/10) are blocked."""
        assert is_private_ip(ip) is True

    # Public IPv4 addresses (should NOT be blocked)
    @pytest.mark.parametrize(
        "ip",
        [
            "8.8.8.8",          # Google DNS
            "1.1.1.1",          # Cloudflare DNS
            "208.67.222.222",   # OpenDNS
            "93.184.216.34",    # example.com
            "142.250.80.46",    # google.com
            "104.16.132.229",   # cloudflare.com
            "172.15.255.255",   # Just before 172.16/12 range
            "172.32.0.0",       # Just after 172.31/12 range
            "192.167.255.255",  # Just before 192.168/16 range
            "192.169.0.0",      # Just after 192.168/16 range
        ],
    )
    def test_public_ipv4_allowed(self, ip: str) -> None:
        """Test that public IPv4 addresses are allowed."""
        assert is_private_ip(ip) is False

    # Public IPv6 addresses (should NOT be blocked)
    @pytest.mark.parametrize(
        "ip",
        [
            "2001:4860:4860::8888",  # Google DNS
            "2606:4700:4700::1111",  # Cloudflare DNS
            "2620:fe::fe",           # Quad9 DNS
            "2001:db8::1",           # Documentation range (but not private)
        ],
    )
    def test_public_ipv6_allowed(self, ip: str) -> None:
        """Test that public IPv6 addresses are allowed."""
        assert is_private_ip(ip) is False

    # Malformed IP addresses
    @pytest.mark.parametrize(
        "ip",
        [
            "",
            "not-an-ip",
            "256.256.256.256",
            "1.2.3.4.5",
            "1.2.3",
            "abc.def.ghi.jkl",
            "::gggg",
            "12345::6789::abcd",
            "192.168.1",
            "192.168.1.1.1",
            "192.168.1.-1",
            "192.168.1.256",
            "-1.0.0.0",
            "hostname.local",
            "localhost",
        ],
    )
    def test_malformed_ip_returns_false(self, ip: str) -> None:
        """Test that malformed IP addresses return False (not private).

        Malformed IPs return False because they can't be validated as
        being in a private range. URL validation will catch these later.
        """
        assert is_private_ip(ip) is False

    def test_blocked_ip_ranges_defined(self) -> None:
        """Test that all expected IP ranges are defined in BLOCKED_IP_RANGES."""
        # Should have at least the documented ranges
        assert len(BLOCKED_IP_RANGES) >= 8

        # Check for specific ranges by checking sample IPs
        samples = [
            ("127.0.0.1", "loopback"),
            ("10.0.0.1", "private class A"),
            ("172.16.0.1", "private class B"),
            ("192.168.0.1", "private class C"),
            ("169.254.0.1", "link-local"),
            ("::1", "IPv6 loopback"),
            ("fc00::1", "IPv6 private"),
            ("fe80::1", "IPv6 link-local"),
        ]
        for ip, description in samples:
            assert is_private_ip(ip), f"{description} ({ip}) should be blocked"


class TestValidateUrlHost:
    """Tests for the validate_url_host function."""

    def test_valid_public_url(self) -> None:
        """Test that valid public URLs pass validation."""
        # Mock DNS resolution to return a public IP
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            # Should not raise
            validate_url_host("https://example.com/path")

    def test_url_without_hostname_raises(self) -> None:
        """Test that URLs without hostnames raise FetchError."""
        with pytest.raises(FetchError, match="no hostname"):
            validate_url_host("file:///etc/passwd")

    def test_url_with_empty_hostname_raises(self) -> None:
        """Test that URLs with empty hostnames raise FetchError."""
        with pytest.raises(FetchError, match="no hostname"):
            validate_url_host("http:///path")

    def test_dns_resolution_to_private_ipv4_raises(self) -> None:
        """Test that DNS resolution to private IPv4 raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://internal.example.com")

    def test_dns_resolution_to_loopback_raises(self) -> None:
        """Test that DNS resolution to loopback raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://localhost")

    def test_dns_resolution_to_link_local_raises(self) -> None:
        """Test that DNS resolution to link-local (AWS metadata) raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://metadata.aws.internal")

    def test_dns_resolution_to_private_ipv6_raises(self) -> None:
        """Test that DNS resolution to private IPv6 raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fc00::1", 0, 0, 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://internal-v6.example.com")

    def test_dns_resolution_to_ipv6_loopback_raises(self) -> None:
        """Test that DNS resolution to IPv6 loopback raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://localhost6")

    def test_dns_resolution_failure_raises(self) -> None:
        """Test that DNS resolution failure raises FetchError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror(8, "Name or service not known")
            with pytest.raises(FetchError, match="Failed to resolve hostname"):
                validate_url_host("https://nonexistent.invalid.domain")

    def test_multiple_dns_records_all_checked(self) -> None:
        """Test that all DNS records are checked, not just the first."""
        with patch("socket.getaddrinfo") as mock_dns:
            # First IP is public, second is private
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0)),
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://multi-record.example.com")

    def test_all_public_dns_records_allowed(self) -> None:
        """Test that multiple public DNS records are all allowed."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.4.4", 0)),
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("2001:4860:4860::8888", 0, 0, 0)),
            ]
            # Should not raise
            validate_url_host("https://multi-public.example.com")

    def test_ipv4_and_ipv6_mixed_records(self) -> None:
        """Test handling of mixed IPv4 and IPv6 records."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0)),
            ]
            # Should not raise
            validate_url_host("https://example.com")

    def test_error_message_includes_hostname_and_ip(self) -> None:
        """Test that error message includes helpful information."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))
            ]
            try:
                validate_url_host("https://evil.example.com")
                pytest.fail("Expected FetchError")
            except FetchError as e:
                error_msg = str(e)
                assert "evil.example.com" in error_msg
                assert "127.0.0.1" in error_msg


class TestUrlHostExtraction:
    """Tests for URL host extraction edge cases."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "https://example.com/",
            "https://example.com/path",
            "https://example.com/path?query=1",
            "https://example.com:443/path",
            "https://user:pass@example.com/path",
        ],
    )
    def test_various_url_formats(self, url: str) -> None:
        """Test host extraction from various URL formats."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            # Should not raise - host should be extracted correctly
            validate_url_host(url)
            # Verify the hostname was resolved
            mock_dns.assert_called_once()
            call_args = mock_dns.call_args[0]
            assert call_args[0] == "example.com"

    def test_url_with_port(self) -> None:
        """Test that port in URL doesn't affect host extraction."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ]
            validate_url_host("https://example.com:8080/path")
            call_args = mock_dns.call_args[0]
            assert call_args[0] == "example.com"

    def test_ipv4_literal_in_url_private(self) -> None:
        """Test that private IPv4 literals in URLs are blocked."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://192.168.1.1/admin")

    def test_ipv4_literal_in_url_public(self) -> None:
        """Test that public IPv4 literals in URLs are allowed."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0))
            ]
            # Should not raise
            validate_url_host("https://8.8.8.8/")

    def test_ipv6_literal_in_url_private(self) -> None:
        """Test that private IPv6 literals in URLs are blocked."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fc00::1", 0, 0, 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                validate_url_host("https://[fc00::1]/admin")


class TestDNSRebindingDocumentation:
    """Tests documenting TOCTOU/DNS rebinding limitations.

    These tests document the known limitation that DNS rebinding attacks
    cannot be fully prevented with the current approach. The validate_url_host
    function resolves DNS at validation time, but aiohttp may resolve again
    when making the actual request.
    """

    def test_toctou_limitation_documented(self) -> None:
        """Verify the TOCTOU limitation is documented in the code."""
        import inspect
        from code_forge.web.fetch.fetcher import validate_url_host

        docstring = inspect.getdoc(validate_url_host)
        assert docstring is not None
        assert "TOCTOU" in docstring or "time-of-check" in docstring.lower()
        assert "DNS rebinding" in docstring.lower() or "rebind" in docstring.lower()

    def test_defense_in_depth_acknowledged(self) -> None:
        """Verify this is described as defense-in-depth, not complete mitigation."""
        import inspect
        from code_forge.web.fetch.fetcher import validate_url_host

        docstring = inspect.getdoc(validate_url_host)
        assert docstring is not None
        assert "defense-in-depth" in docstring.lower() or "not a complete" in docstring.lower()


class TestIntegrationWithFetcher:
    """Integration tests verifying SSRF protection in the full fetch flow."""

    @pytest.mark.asyncio
    async def test_fetch_blocks_private_ip(self) -> None:
        """Test that fetch() blocks requests to private IPs."""
        from code_forge.web.fetch.fetcher import URLFetcher

        fetcher = URLFetcher()

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                await fetcher.fetch("https://internal.example.com")

    @pytest.mark.asyncio
    async def test_fetch_blocks_localhost(self) -> None:
        """Test that fetch() blocks requests to localhost."""
        from code_forge.web.fetch.fetcher import URLFetcher

        fetcher = URLFetcher()

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                await fetcher.fetch("https://localhost/admin")

    @pytest.mark.asyncio
    async def test_fetch_blocks_aws_metadata(self) -> None:
        """Test that fetch() blocks requests to AWS metadata endpoint."""
        from code_forge.web.fetch.fetcher import URLFetcher

        fetcher = URLFetcher()

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))
            ]
            with pytest.raises(FetchError, match="internal/private IP"):
                await fetcher.fetch("http://169.254.169.254/latest/meta-data/")

    @pytest.mark.asyncio
    async def test_http_upgraded_before_ssrf_check(self) -> None:
        """Test that HTTP is upgraded to HTTPS before SSRF validation."""
        from code_forge.web.fetch.fetcher import URLFetcher

        fetcher = URLFetcher()

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ]
            # Even HTTP URLs should trigger SSRF check
            with pytest.raises(FetchError, match="internal/private IP"):
                await fetcher.fetch("http://internal.example.com")
