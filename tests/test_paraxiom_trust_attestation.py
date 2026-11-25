import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from paraxiom_trust import AttestationLayer, ParaxiomTrustConfig, TrustLayerError

try:
    import pqcrypto.sign.ml_dsa_87  # noqa: F401
    HAS_PQCRYPTO = True
except ImportError:
    HAS_PQCRYPTO = False


ARTIFACT = {
    'artifact_id': 'a1',
    'producer_agent': 'TestAgent',
    'skill_used': 'blast',
    'parent_artifact_ids': ['a0'],
    'investigation_id': 'inv1',
    'payload': {'result': 42},
}

NO_PQCRYPTO = {'pqcrypto': None, 'pqcrypto.sign': None, 'pqcrypto.sign.ml_dsa_87': None}


class TrustLayerTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.config = ParaxiomTrustConfig(
            signing_enabled=True,
            key_dir=str(self.root / 'keys'),
            attestation_log=str(self.root / 'attestations.jsonl'),
        )
        self.agent_dir = self.root / 'keys' / 'TestAgent'


class TestTrustLayerFailsClosed(TrustLayerTestCase):
    def test_signing_is_off_by_default(self):
        self.assertFalse(ParaxiomTrustConfig().signing_enabled)

    def test_disabled_layer_refuses_to_attest(self):
        self.config.signing_enabled = False
        layer = AttestationLayer('TestAgent', self.config)
        with self.assertRaises(TrustLayerError):
            layer.attest(dict(ARTIFACT))
        self.assertFalse(self.agent_dir.exists())

    def test_old_falcon_setting_is_rejected(self):
        self.config.sign_algorithm = 'falcon512'
        with self.assertRaises(TrustLayerError):
            AttestationLayer('TestAgent', self.config)

    def test_missing_library_raises_instead_of_falling_back(self):
        with patch.dict(sys.modules, NO_PQCRYPTO):
            with self.assertRaises(TrustLayerError):
                AttestationLayer('TestAgent', self.config)
        self.assertFalse(self.agent_dir.exists())


@unittest.skipUnless(HAS_PQCRYPTO, 'pqcrypto not installed')
class TestTrustLayerSigning(TrustLayerTestCase):
    def setUp(self):
        super().setUp()
        self.layer = AttestationLayer('TestAgent', self.config)
        self.att = self.layer.attest(dict(ARTIFACT))

    def test_round_trip(self):
        self.assertEqual(self.att.signature_algorithm, 'ml-dsa-87')
        self.assertEqual(len(bytes.fromhex(self.att.signature)), 4627)
        self.assertTrue(self.layer.verify(self.att, dict(ARTIFACT)))

    def test_key_is_reused_across_instances(self):
        again = AttestationLayer('TestAgent', self.config)
        self.assertTrue(again.verify(self.att, dict(ARTIFACT)))

    def test_attestation_is_logged(self):
        self.assertIn('"ml-dsa-87"', Path(self.config.attestation_log).read_text())

    def test_tampered_payload_fails(self):
        self.assertFalse(self.layer.verify(self.att, dict(ARTIFACT, payload={'result': 43})))

    def test_tampered_lineage_fails(self):
        self.att.parent_artifact_ids = ['forged']
        self.assertFalse(self.layer.verify(self.att, dict(ARTIFACT)))

    def test_flipped_signature_byte_fails(self):
        sig = bytearray.fromhex(self.att.signature)
        sig[100] ^= 1
        self.att.signature = sig.hex()
        self.assertFalse(self.layer.verify(self.att, dict(ARTIFACT)))

    def test_legacy_hmac_record_fails(self):
        self.att.signature = 'hmac_' + '00' * 32
        self.assertFalse(self.layer.verify(self.att, dict(ARTIFACT)))
        self.att.signature_algorithm = 'falcon512'
        self.assertFalse(self.layer.verify(self.att, dict(ARTIFACT)))

    def test_record_from_another_key_fails(self):
        other = AttestationLayer('OtherAgent', self.config)
        self.assertFalse(self.layer.verify(other.attest(dict(ARTIFACT)), dict(ARTIFACT)))

    def test_secret_key_is_owner_only(self):
        mode = (self.agent_dir / 'ml-dsa-87.sk').stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_legacy_key_files_are_ignored(self):
        legacy_dir = self.root / 'keys' / 'LegacyAgent'
        legacy_dir.mkdir(parents=True)
        (legacy_dir / 'signing_key.bin').write_bytes(os.urandom(1281))
        (legacy_dir / 'verification_key.bin').write_bytes(os.urandom(897))
        layer = AttestationLayer('LegacyAgent', self.config)
        self.assertTrue((legacy_dir / 'ml-dsa-87.sk').exists())
        self.assertTrue(layer.verify(layer.attest(dict(ARTIFACT)), dict(ARTIFACT)))

    def test_truncated_key_is_rejected(self):
        (self.agent_dir / 'ml-dsa-87.pk').write_bytes(b'short')
        with self.assertRaises(TrustLayerError):
            AttestationLayer('TestAgent', self.config)

    def test_mismatched_key_pair_is_rejected(self):
        AttestationLayer('OtherAgent', self.config)
        other_pk = (self.root / 'keys' / 'OtherAgent' / 'ml-dsa-87.pk').read_bytes()
        (self.agent_dir / 'ml-dsa-87.pk').write_bytes(other_pk)
        with self.assertRaises(TrustLayerError):
            AttestationLayer('TestAgent', self.config)

    def test_missing_half_of_key_pair_is_rejected(self):
        (self.agent_dir / 'ml-dsa-87.pk').unlink()
        with self.assertRaises(TrustLayerError):
            AttestationLayer('TestAgent', self.config)


class _Artifact:
    artifact_id = 'a1'

    def to_dict(self):
        return dict(ARTIFACT)


class TestArtifactStoreHook(TrustLayerTestCase):
    def setUp(self):
        super().setUp()
        patches = [
            patch.dict(os.environ, {'HOME': str(self.root)}),
            patch('paraxiom_trust.ParaxiomTrustConfig.load', return_value=self.config),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        from artifacts.artifact import ArtifactStore
        self.store = ArtifactStore('TestAgent')
        for name in ('_append_global_index', '_sync_to_infinite'):
            p = patch.object(self.store, name)
            p.start()
            self.addCleanup(p.stop)

    def test_disabled_signing_creates_no_keys(self):
        self.config.signing_enabled = False
        self.assertEqual(self.store.save(_Artifact()), 'a1')
        self.assertFalse(self.agent_dir.exists())

    def test_failed_attestation_warns_and_does_not_block(self):
        with patch.dict(sys.modules, NO_PQCRYPTO):
            with self.assertLogs(level='WARNING') as logs:
                self.assertEqual(self.store.save(_Artifact()), 'a1')
        self.assertIn('was not attested', logs.output[0])


if __name__ == '__main__':
    unittest.main()
