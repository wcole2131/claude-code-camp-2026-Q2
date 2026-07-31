require "fileutils"

# FileSystemTools registers the standard set of file-oriented tools against
# a Boukensha::Registry, all sandboxed to a single root directory.
#
# This used to live inside the Boukensha framework itself, as
# Boukensha::Tools::FileSystem -- it moved here because the framework no
# longer ships any domain tool implementations (see
# docs/plans/mud_manager/mcp_mud_plan.md). This is server-side code now,
# owned by file_system_mcp, not agent-side code.
#
# Tools registered:
#   pwd              — return the working directory
#   list_directory   — list files and subdirectories at a path
#   read_file        — read the full contents of a file
#   write_file       — write (or overwrite) a file
#   delete_file      — delete a file
#   search_files     — grep for a pattern across files in the working tree
#
# Every path argument the agent supplies is resolved relative to that root.
# If the resolved path would escape the root (path traversal) the tool
# returns an error string rather than raising — so the agent sees it and
# can try something sensible instead.
#
# Usage:
#
#   FileSystemTools.register(registry, working_dir: "/my/project")
#
module FileSystemTools
  def self.register(registry, working_dir:)
    root = File.expand_path(working_dir)

    # Resolve a relative (or absolute) agent-supplied path inside root.
    # Returns the absolute path on success, or an error String.
    resolve = lambda do |path|
      absolute = File.expand_path(path.to_s, root)
      if absolute == root || absolute.start_with?("#{root}/")
        absolute
      else
        "error: path '#{path}' escapes the working directory"
      end
    end

    oops = ->(msg) { "error: #{msg}" }

    registry.tool "pwd",
      description: "Return the working directory — the root that all file paths are relative to.",
      parameters:  {} do
      root
    end

    registry.tool "list_directory",
      description: "List files and subdirectories at a path relative to the working directory. Defaults to the working directory itself.",
      parameters:  {
        path: { type: "string", description: "Relative path to list (default '.')", required: false }
      } do |path: "."|
      target = resolve.call(path)
      next target if target.start_with?("error:")
      next oops.call("'#{path}' is not a directory") unless File.directory?(target)

      entries = Dir.entries(target)
                   .reject { |e| e == "." || e == ".." }
                   .sort
                   .map { |name| File.directory?(File.join(target, name)) ? "#{name}/" : name }

      entries.empty? ? "(empty)" : entries.join("\n")
    end

    registry.tool "read_file",
      description: "Read and return the full contents of a file. Path is relative to the working directory.",
      parameters:  {
        path: { type: "string", description: "Relative path to the file" }
      } do |path:|
      target = resolve.call(path)
      next target if target.start_with?("error:")
      next oops.call("'#{path}' is not a file") unless File.file?(target)

      content = File.read(target)
      # Content crosses the wire as a JSON string (MCP content blocks are
      # text-only); an invalid byte sequence would otherwise surface as a
      # confusing JSON encoding error downstream instead of a clean one here.
      next oops.call("file is not valid UTF-8 text") unless content.valid_encoding?

      content
    rescue => e
      oops.call(e.message)
    end

    registry.tool "write_file",
      description: "Write content to a file, creating it (and any missing parent directories) if needed, overwriting if it exists. Path is relative to the working directory.",
      parameters:  {
        path:    { type: "string", description: "Relative path to the file" },
        content: { type: "string", description: "Text content to write" }
      } do |path:, content:|
      target = resolve.call(path)
      next target if target.start_with?("error:")

      FileUtils.mkdir_p(File.dirname(target))
      File.write(target, content)
      rel = target.delete_prefix("#{root}/")
      "ok: wrote #{content.bytesize} bytes to #{rel}"
    rescue => e
      oops.call(e.message)
    end

    registry.tool "delete_file",
      description: "Delete a file. Directories are not deleted. Path is relative to the working directory.",
      parameters:  {
        path: { type: "string", description: "Relative path to the file to delete" }
      } do |path:|
      target = resolve.call(path)
      next target if target.start_with?("error:")
      next oops.call("'#{path}' is not a file") unless File.file?(target)

      File.delete(target)
      "ok: deleted #{path}"
    rescue => e
      oops.call(e.message)
    end

    registry.tool "search_files",
      description: "Search for a text pattern (literal string or Ruby regex) across all files in the working directory tree. Returns matching lines in 'path:line_number:content' format.",
      parameters:  {
        pattern: { type: "string", description: "The text or regex pattern to search for" },
        path:    { type: "string", description: "Subdirectory or file to search within (default '.' = entire working directory)", required: false },
        glob:    { type: "string", description: "File glob to restrict which files are searched, e.g. '*.rb' (default '*')", required: false }
      } do |pattern:, path: ".", glob: "*"|
      target = resolve.call(path)
      next target if target.start_with?("error:")

      file_glob = File.file?(target) ? target : File.join(target, "**", glob)

      begin
        regex = Regexp.new(pattern)
      rescue RegexpError => e
        next oops.call("invalid pattern: #{e.message}")
      end

      matches = []
      Dir.glob(file_glob).sort.each do |file|
        next unless File.file?(file)

        rel = file.delete_prefix("#{root}/")
        begin
          File.foreach(file).with_index(1) do |line, lineno|
            matches << "#{rel}:#{lineno}:#{line.chomp}" if line.match?(regex)
          end
        rescue => e
          matches << "#{rel}: error reading file: #{e.message}"
        end
      end

      matches.empty? ? "no matches" : matches.join("\n")
    end
  end # def self.register
end # FileSystemTools
