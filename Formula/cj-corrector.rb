class CjCorrector < Formula
  desc "Czech grammar correction macOS menu bar app"
  homepage "https://github.com/antoninsiska/cj-correcter"
  url "https://github.com/antoninsiska/cj-correcter/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "b018784b2b0473e528b9551e0a0a26ea7ee284665bbfc5ae505dae8e897173bb"
  license "MIT"

  depends_on :macos
  depends_on "python@3.12"

  def install
    system "python3.12", "-m", "venv", libexec
    system libexec/"bin/pip", "install", "rumps", "requests", "matplotlib", "torch", "transformers"

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
