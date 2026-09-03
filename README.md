# valet.sh

> [!WARNING]
> **macOS: valet.sh 2.x has reached the end of its technical life.**
>
> valet.sh 2.x builds its macOS environment on the `x86_64` build of Homebrew - natively on Intel Macs
> and through Rosetta 2 on Apple Silicon. Since September 2026 Homebrew no longer builds Intel bottles,
> so core dependencies such as `openssl@3`, `curl` and `pcre2` have to be compiled from source on every
> machine - slow and increasingly likely to fail. **valet.sh 2.x therefore receives no further
> maintenance on macOS.**
>
> - **Apple Silicon** - switch to [valet.sh 3.x](https://valet.sh/3.x/), it runs natively on arm64. See the
>   [upgrade guide](https://valet.sh/3.x/getting-started/upgrade-from-2x/).
> - **Intel Mac** - no upgrade path, valet.sh 3.x supports Apple Silicon only. Existing installations keep
>   working as long as their packages do, but avoid `brew upgrade`.
> - **Ubuntu** - not affected, the Linux side does not use Homebrew.
>
> Full explanation: [valet.sh documentation](https://valet.sh/)

## Documentation

See https://valet.sh

## Installation

for Ubuntu and MacOS (Intel)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/valet-sh/install/2.x/install.sh)
```

At the moment valet.sh on Apple m1 requires rosetta2:
```bash
/usr/sbin/softwareupdate --install-rosetta --agree-to-license
bash <(curl -fsSL https://raw.githubusercontent.com/valet-sh/install/2.x/install.sh)
```

## Usage

See command descriptions when executing `valet.sh`

```bash
Usage:
  command [options] [command] [arguments]
```
