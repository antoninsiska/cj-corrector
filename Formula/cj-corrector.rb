class CjCorrector < Formula
  desc "Czech grammar correction macOS menu bar app"
  homepage "https://github.com/antoninsiska/cj-correcter"
  url "https://github.com/antoninsiska/cj-correcter/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "233c19319c4e3cced0cc2832d45d10f650f6d748bdc748f6b9668e132c61ee9d"
  license "MIT"

  depends_on :macos
  depends_on "python@3.12"

  def install
    system "python3.12", "-m", "venv", libexec
    # Install torch with MPS support (Apple Silicon) and other deps
    system libexec/"bin/pip", "install", "--upgrade", "pip"
    system libexec/"bin/pip", "install",
      "pyobjc-core",
      "pyobjc-framework-Cocoa",
      "pyobjc-framework-ApplicationServices",
      "rumps",
      "requests",
      "matplotlib"
    system libexec/"bin/pip", "install",
      "--index-url", "https://download.pytorch.org/whl/cpu",
      "torch"
    system libexec/"bin/pip", "install", "transformers"

    libexec.install Dir["*.py"]

    (bin/"cj-correcter").write <<~EOS
      #!/bin/bash
      exec "#{libexec}/bin/python3" "#{libexec}/app.py" "$@"
    EOS
  end

  def caveats
    <<~EOS
      Spuštění:
        cj-correcter &

      Přidání do Login Items (automatický start):
        System Settings → General → Login Items → klikni + → vyber cj-correcter
    EOS
  end

  test do
    assert_predicate libexec/"app.py", :exist?
  end
end
