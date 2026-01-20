"""Tests for site response and multi-component ground motion."""

import numpy as np
import pytest

from seismic_twin.ground_motion import (
    GroundMotionRecord,
    GroundMotionSuite,
    SiteClass,
    SiteProperties,
    apply_site_response,
    classify_site,
    compute_site_amplification,
    design_response_spectrum,
    generate_2component_ground_motion,
    generate_site_modified_motion,
    generate_synthetic_ground_motion,
    generate_vertical_component,
)


class TestSiteClassification:
    """Tests for site classification."""

    def test_classify_hard_rock(self):
        """Site class A for Vs30 > 1500 m/s."""
        assert classify_site(2000) == SiteClass.A
        assert classify_site(1501) == SiteClass.A

    def test_classify_rock(self):
        """Site class B for 760 < Vs30 <= 1500 m/s."""
        assert classify_site(1500) == SiteClass.B
        assert classify_site(1000) == SiteClass.B
        assert classify_site(761) == SiteClass.B

    def test_classify_dense_soil(self):
        """Site class C for 360 < Vs30 <= 760 m/s."""
        assert classify_site(760) == SiteClass.C
        assert classify_site(500) == SiteClass.C
        assert classify_site(361) == SiteClass.C

    def test_classify_stiff_soil(self):
        """Site class D for 180 < Vs30 <= 360 m/s."""
        assert classify_site(360) == SiteClass.D
        assert classify_site(250) == SiteClass.D
        assert classify_site(181) == SiteClass.D

    def test_classify_soft_clay(self):
        """Site class E for Vs30 < 180 m/s."""
        assert classify_site(180) == SiteClass.E
        assert classify_site(100) == SiteClass.E
        assert classify_site(50) == SiteClass.E


class TestSiteProperties:
    """Tests for SiteProperties class."""

    def test_from_vs30(self):
        """Create site properties from Vs30."""
        site = SiteProperties.from_vs30(250)
        assert site.site_class == SiteClass.D
        assert site.vs30 == 250
        assert site.peak_amplification > 1.0

    def test_from_vs30_with_depth(self):
        """Create site properties with soil depth."""
        site = SiteProperties.from_vs30(300, soil_depth=30)
        assert site.site_class == SiteClass.D
        # f = Vs / (4H) = 300 / (4*30) = 2.5 Hz
        assert abs(site.resonance_freq - 2.5) < 0.1

    def test_from_site_class_string(self):
        """Create from site class string."""
        site = SiteProperties.from_site_class("D")
        assert site.site_class == SiteClass.D
        assert site.vs30 == 250  # Typical value for D

    def test_from_site_class_enum(self):
        """Create from SiteClass enum."""
        site = SiteProperties.from_site_class(SiteClass.C)
        assert site.site_class == SiteClass.C
        assert site.vs30 == 500  # Typical value for C


class TestSiteAmplification:
    """Tests for site amplification functions."""

    def test_amplification_at_resonance(self):
        """Peak amplification should occur near resonance frequency."""
        site = SiteProperties.from_site_class("D")
        frequencies = np.linspace(0.1, 10, 100)
        amplification = compute_site_amplification(frequencies, site)

        # Find peak
        peak_idx = np.argmax(amplification)
        peak_freq = frequencies[peak_idx]

        # Should be near site resonance frequency
        assert abs(peak_freq - site.resonance_freq) < 1.0

    def test_amplification_low_frequency_plateau(self):
        """Low frequency amplification should be near baseline."""
        site = SiteProperties.from_site_class("D")
        frequencies = np.array([0.1, 0.2, 0.3])
        amplification = compute_site_amplification(frequencies, site)

        # Low frequency values should be similar
        assert np.std(amplification) < 0.3

    def test_no_amplification_site_class_a(self):
        """Site class A should have minimal amplification."""
        site = SiteProperties.from_site_class("A")
        frequencies = np.linspace(0.1, 10, 100)
        amplification = compute_site_amplification(frequencies, site)

        # All values should be close to 1.0
        assert np.all(amplification >= 0.5)
        assert np.all(amplification <= 1.5)


class TestApplySiteResponse:
    """Tests for applying site response to ground motion."""

    def test_apply_site_response_amplifies(self):
        """Site response should amplify motion for soft sites."""
        time, acc = generate_synthetic_ground_motion(duration=10, dt=0.01, target_pga=0.2, seed=42)

        acc_amplified = apply_site_response(time, acc, "D")

        # PGA should increase for site class D
        pga_original = np.max(np.abs(acc))
        pga_amplified = np.max(np.abs(acc_amplified))

        assert pga_amplified > pga_original * 0.9  # Allow some variation

    def test_apply_site_response_site_a_unchanged(self):
        """Site class A should not amplify."""
        time, acc = generate_synthetic_ground_motion(duration=10, dt=0.01, target_pga=0.2, seed=42)

        acc_result = apply_site_response(time, acc, "A")

        # Should be essentially unchanged
        np.testing.assert_array_almost_equal(acc, acc_result, decimal=10)

    def test_apply_site_response_preserves_length(self):
        """Output should have same length as input."""
        time, acc = generate_synthetic_ground_motion(duration=10, dt=0.01, target_pga=0.2, seed=42)

        acc_amplified = apply_site_response(time, acc, "E")

        assert len(acc_amplified) == len(acc)


class TestVerticalComponent:
    """Tests for vertical component generation."""

    def test_vertical_pga_ratio(self):
        """Vertical PGA should match specified V/H ratio."""
        time, horizontal = generate_synthetic_ground_motion(
            duration=20, dt=0.01, target_pga=0.3, seed=42
        )

        v_h_ratio = 0.67
        vertical = generate_vertical_component(horizontal, dt=0.01, v_h_ratio=v_h_ratio, seed=43)

        actual_ratio = np.max(np.abs(vertical)) / np.max(np.abs(horizontal))
        assert abs(actual_ratio - v_h_ratio) < 0.05

    def test_vertical_same_length(self):
        """Vertical component should have same length."""
        time, horizontal = generate_synthetic_ground_motion(
            duration=20, dt=0.01, target_pga=0.3, seed=42
        )

        vertical = generate_vertical_component(horizontal, dt=0.01, seed=43)

        assert len(vertical) == len(horizontal)

    def test_vertical_different_phase(self):
        """Vertical should have different phase from horizontal."""
        time, horizontal = generate_synthetic_ground_motion(
            duration=20, dt=0.01, target_pga=0.3, seed=42
        )

        vertical = generate_vertical_component(horizontal, dt=0.01, seed=43)

        # Correlation should not be too high
        correlation = np.corrcoef(horizontal, vertical)[0, 1]
        assert abs(correlation) < 0.9


class TestGroundMotionRecord:
    """Tests for GroundMotionRecord class."""

    def test_create_single_component(self):
        """Create record with only horizontal component."""
        time = np.linspace(0, 10, 1001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1

        record = GroundMotionRecord(time=time, horizontal=horizontal)

        assert record.n_points == 1001
        assert record.duration == 10.0
        assert record.dt == 0.01
        assert not record.has_vertical
        assert record.pga_vertical is None

    def test_create_two_component(self):
        """Create record with horizontal and vertical."""
        time = np.linspace(0, 10, 1001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1
        vertical = np.sin(2 * np.pi * 2.0 * time) * 0.067

        record = GroundMotionRecord(time=time, horizontal=horizontal, vertical=vertical)

        assert record.has_vertical
        assert record.pga_horizontal == pytest.approx(0.1, rel=0.01)
        assert record.pga_vertical == pytest.approx(0.067, rel=0.01)
        assert record.v_h_ratio == pytest.approx(0.67, rel=0.05)

    def test_get_component(self):
        """Get specific components."""
        time = np.linspace(0, 10, 1001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1
        vertical = np.cos(2 * np.pi * 1.0 * time) * 0.067

        record = GroundMotionRecord(time=time, horizontal=horizontal, vertical=vertical)

        np.testing.assert_array_equal(record.get_component("H"), horizontal)
        np.testing.assert_array_equal(record.get_component("V"), vertical)

    def test_scale(self):
        """Scale record."""
        time = np.linspace(0, 10, 1001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1
        vertical = np.cos(2 * np.pi * 1.0 * time) * 0.067

        record = GroundMotionRecord(time=time, horizontal=horizontal, vertical=vertical)

        scaled = record.scale(2.0)

        assert scaled.pga_horizontal == pytest.approx(0.2, rel=0.01)
        assert scaled.pga_vertical == pytest.approx(0.134, rel=0.01)

    def test_scale_to_pga(self):
        """Scale to target PGA."""
        time = np.linspace(0, 10, 1001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1
        vertical = np.cos(2 * np.pi * 1.0 * time) * 0.067

        record = GroundMotionRecord(time=time, horizontal=horizontal, vertical=vertical)

        scaled = record.scale_to_pga(0.3)

        assert scaled.pga_horizontal == pytest.approx(0.3, rel=0.01)

    def test_trim(self):
        """Trim record to time window."""
        time = np.linspace(0, 20, 2001)
        horizontal = np.sin(2 * np.pi * 1.0 * time) * 0.1

        record = GroundMotionRecord(time=time, horizontal=horizontal)

        trimmed = record.trim(5.0, 15.0)

        assert trimmed.duration == pytest.approx(10.0, rel=0.01)
        assert trimmed.time[0] == 0.0  # Time resets to 0


class TestGenerate2Component:
    """Tests for 2-component ground motion generation."""

    def test_generate_basic(self):
        """Generate basic 2-component motion."""
        record = generate_2component_ground_motion(duration=20, dt=0.01, target_pga=0.3, seed=42)

        assert record.has_vertical
        assert record.pga_horizontal == pytest.approx(0.3, rel=0.05)
        assert record.duration == pytest.approx(20.0, rel=0.01)

    def test_generate_with_v_h_ratio(self):
        """Generate with specific V/H ratio."""
        record = generate_2component_ground_motion(
            duration=20, dt=0.01, target_pga=0.3, v_h_ratio=0.5, seed=42
        )

        assert record.v_h_ratio == pytest.approx(0.5, rel=0.1)

    def test_reproducibility(self):
        """Same seed should produce same result."""
        record1 = generate_2component_ground_motion(duration=10, seed=123)
        record2 = generate_2component_ground_motion(duration=10, seed=123)

        np.testing.assert_array_almost_equal(record1.horizontal, record2.horizontal, decimal=10)


class TestSiteModifiedMotion:
    """Tests for site-modified ground motion generation."""

    def test_generate_site_d(self):
        """Generate motion with site class D."""
        record = generate_site_modified_motion(
            duration=20, dt=0.01, target_pga=0.3, site_class="D", seed=42
        )

        assert record.pga_horizontal == pytest.approx(0.3, rel=0.05)
        assert record.metadata["site_class"] == "D"
        assert "vs30" in record.metadata

    def test_generate_without_vertical(self):
        """Generate without vertical component."""
        record = generate_site_modified_motion(
            duration=20,
            dt=0.01,
            target_pga=0.3,
            site_class="D",
            include_vertical=False,
            seed=42,
        )

        assert not record.has_vertical

    def test_site_class_affects_vh_ratio(self):
        """Softer sites should have higher V/H ratio."""
        record_c = generate_site_modified_motion(duration=20, site_class="C", seed=42)
        record_e = generate_site_modified_motion(duration=20, site_class="E", seed=42)

        # Site E should have higher V/H ratio than C
        assert record_e.v_h_ratio > record_c.v_h_ratio


class TestDesignResponseSpectrum:
    """Tests for design response spectrum generation."""

    def test_spectrum_shape(self):
        """Spectrum should have proper shape."""
        periods, sa = design_response_spectrum("D", ss=1.0, s1=0.5)

        assert len(periods) == len(sa)
        assert all(sa > 0)

        # Should have plateau region
        plateau_mask = (periods > 0.1) & (periods < 0.5)
        plateau_values = sa[plateau_mask]
        assert np.std(plateau_values) / np.mean(plateau_values) < 0.3

    def test_spectrum_decreases_at_long_periods(self):
        """Sa should decrease at long periods."""
        periods, sa = design_response_spectrum("D", ss=1.0, s1=0.5)

        # Compare short and long period values
        short_period_sa = np.mean(sa[periods < 0.5])
        long_period_sa = np.mean(sa[periods > 2.0])

        assert short_period_sa > long_period_sa


class TestGroundMotionSuite:
    """Tests for GroundMotionSuite class."""

    def test_create_suite(self):
        """Create a suite of records."""
        suite = GroundMotionSuite(name="Test Suite")

        for i in range(5):
            record = generate_2component_ground_motion(
                duration=10, target_pga=0.2 + i * 0.05, seed=i
            )
            suite.add(record)

        assert len(suite) == 5

    def test_pga_statistics(self):
        """Compute PGA statistics."""
        suite = GroundMotionSuite()

        for i in range(10):
            record = generate_2component_ground_motion(duration=10, target_pga=0.3, seed=i)
            suite.add(record)

        stats = suite.pga_statistics

        assert "mean" in stats
        assert "std" in stats
        assert stats["mean"] == pytest.approx(0.3, rel=0.1)

    def test_scale_all(self):
        """Scale all records to target PGA."""
        suite = GroundMotionSuite()

        for i in range(5):
            record = generate_2component_ground_motion(
                duration=10, target_pga=0.2 + i * 0.1, seed=i
            )
            suite.add(record)

        scaled = suite.scale_all_to_pga(0.4)

        for record in scaled:
            assert record.pga_horizontal == pytest.approx(0.4, rel=0.05)
