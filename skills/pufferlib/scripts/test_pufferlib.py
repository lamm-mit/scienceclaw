#!/usr/bin/env python3
"""
Test pufferlib skill: verify import and optional minimal env.
Exit 0 if OK, 1 with message if pufferlib missing or broken.
Install: pip install pufferlib (build may require CUDA_HOME).
"""
import sys
if '--help' in sys.argv or '-h' in sys.argv:
    print("PufferLib skill test - verify import and optional env")
    print("Usage: python test_pufferlib.py [--env]")
    print("Install: pip install pufferlib")
    sys.exit(0)


def main():
    try:
        import pufferlib
    except ImportError as e:
        print("pufferlib skill test: FAIL (missing dependency)", file=sys.stderr)
        print("  pip install pufferlib", file=sys.stderr)
        print("  Note: building from source may require CUDA_HOME.", file=sys.stderr)
        return 1

    try:
        from pufferlib import PuffeRL
        from pufferlib import PufferEnv
    except ImportError as e:
        print("pufferlib skill test: FAIL (incomplete install)", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1

    print("pufferlib skill test: import OK")
    if "--env" in sys.argv:
        try:
            env = pufferlib.make("gym-CartPole-v1", num_envs=2)
            env.reset()
            env.close()
            print("pufferlib skill test: minimal env OK")
        except Exception as e:
            print(f"pufferlib skill test: env check failed: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
