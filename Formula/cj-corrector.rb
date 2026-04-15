class CjCorrector < Formula
  desc "Czech grammar correction macOS menu bar app"
  homepage "https://github.com/antoninsiska/cj-corrector"
  url "https://github.com/antoninsiska/cj-corrector/archive/refs/tags/v1.0.4.tar.gz"
  sha256 "28ed96cc3955302c65dfa125562ab27cf03c856468ef511a68c5852a678e7e6e"
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
