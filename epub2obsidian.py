import os
import re
import subprocess
import argparse

def step_1(epub_path, attachments_dir, outfile_path):
    """
    Step 1: Convert an ePUB (or PDF) to a single Markdown file using Pandoc.

    :param epub_path: Path to the input ePUB (or PDF).
    :param attachments_dir: Directory to store extracted attachments (images).
    :param outfile_path: Path for the generated Markdown file.
    :return: None
    """
    os.makedirs(attachments_dir, exist_ok=True)
    pandoc_command = f"""
    pandoc \
        -t gfm-raw_html \
        --wrap=none \
        --extract-media={attachments_dir} \
        -s "{epub_path}" \
        -o "{outfile_path}"
    """
    print(f"[Step 1] Running:\n{pandoc_command}")
    subprocess.run(pandoc_command, shell=True, check=False)
    print("[*] If the resulting Markdown file contains artifacts, consider using Pandoc Lua filters or manual edits.")
    print("[+] Step 1 done.\n")


def step_2(outfile_path, outdir_path, heading_lvl):
    """
    Step 2: Split a single Markdown file into multiple smaller files based on a specified heading level.
             The note filename will use the heading text (with illegal filename characters removed) and no extra numbering.

    :param outfile_path: Path to the single combined Markdown file.
    :param outdir_path: Directory in which to write the split Markdown files.
    :param heading_lvl: Numeric string representing the heading level to split on.
                        '1' means '#' headings, '2' means '##', etc.
    :return: A list of note file paths created, in the order they appear in the original file.
    """
    print(f"[Step 2] Splitting Markdown on heading level {heading_lvl}...")
    os.makedirs(outdir_path, exist_ok=True)
    
    with open(outfile_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    heading_str = "#" * int(heading_lvl)
    
    # Record the line indices of headings at the specified level
    split_indices = [idx for idx, line in enumerate(lines) if line.startswith(heading_str + " ")]
    if not split_indices:
        print(f"[Step 2] No headings of level {heading_lvl} found. Skipping split.")
        return []

    note_file_paths = []
    for i, start_index in enumerate(split_indices):
        end_index = split_indices[i + 1] if (i + 1) < len(split_indices) else len(lines)
        chunk_lines = lines[start_index:end_index]
        # Extract heading text (remove the '#' characters and trim spaces)
        heading_text = chunk_lines[0].lstrip("#").strip()
        # Remove characters that are illegal in filenames, but leave spaces intact.
        safe_heading = re.sub(r'[\\/*?:"<>|]', '', heading_text)
        # Construct the filename using safe_heading; add a .md extension.
        note_file_path = os.path.join(outdir_path, f"{safe_heading}.md")
        with open(note_file_path, "w", encoding="utf-8") as note_file:
            note_file.write("\n".join(chunk_lines))
            note_file.write("\n")
        note_file_paths.append(note_file_path)
    
    print(f"[+] Step 2 done. Created {len(note_file_paths)} note file(s).\n")
    return note_file_paths


def step_3(note_files, metadata_path):
    """
    Step 3: Prepend metadata (YAML front matter) to each Markdown file in the provided list.

    :param note_files: List of note file paths.
    :param metadata_path: Path to the YAML template file.
    :return: None
    """
    print("[Step 3] Prepending YAML metadata to each note...")
    with open(metadata_path, "r", encoding="utf-8") as f:
        yaml_template = f.read().strip()
    for note_path in note_files:
        if note_path.lower().endswith(".md"):
            with open(note_path, "r", encoding="utf-8") as note_file:
                original_content = note_file.read()
            new_content = f"{yaml_template}\n\n{original_content}"
            with open(note_path, "w", encoding="utf-8") as note_file:
                note_file.write(new_content)
    print("[+] Step 3 done.\n")


def step_4(note_files, resources_path):
    """
    Step 4: Append a "Resources" section from a Markdown template to each note,
            replacing <NEXT_NOTE_LINK> with a link to the next note.

    :param note_files: List of note file paths, ordered as they appear.
    :param resources_path: Path to the Markdown file containing the Resources section.
    :return: None
    """
    print("[Step 4] Appending Resources section to each note...")
    with open(resources_path, "r", encoding="utf-8") as f:
        resources_base = f.read().strip()
    for i, current_note in enumerate(note_files):
        if i < len(note_files) - 1:
            next_note = note_files[i+1]
            next_name = os.path.basename(next_note)
            next_name_no_ext = os.path.splitext(next_name)[0]
            next_note_link = f"[[{next_name_no_ext}]]"
        else:
            next_note_link = "N/A"
        resources_content = resources_base.replace("<NEXT_NOTE_LINK>", next_note_link)
        with open(current_note, "r", encoding="utf-8") as note_file:
            original_content = note_file.read()
        new_content = f"{original_content}\n\n{resources_content}\n"
        with open(current_note, "w", encoding="utf-8") as note_file:
            note_file.write(new_content)
    print("[+] Step 4 done.\n")
    print("Final step: Review your notes and then move the notes and attachments into Obsidian.")


def main():
    """
    Main function to parse command-line arguments and execute the conversion pipeline.

    Steps:
      1. (Optional) Convert the source ePUB into a Markdown file and extract media.
      2. Split the Markdown file into multiple chapter notes based on a heading level.
      3. Prepend YAML metadata to each note.
      4. Append a resources section to each note, including a link to the next note.

    Command-line arguments:
      epub           : Path to input ePUB file.
      outfile        : Path for the intermediate Markdown output.
      --attachments  : Directory for attachments (default: "attachments").
      --metadata     : Path to YAML metadata template (default: "templates/metadata.yml").
      --resources    : Path to resources Markdown template (default: "templates/resources.md").
      --outdir       : Output directory for notes (default: "notes").
      --heading_level: Heading level used for splitting the Markdown (default: "1").
      --step-1       : Perform only Step 1 (conversion), then exit.
      --no-step-1    : Skip Step 1 and perform Steps 2 onward.
    """
    parser = argparse.ArgumentParser(
        description="Convert an ePUB file into Obsidian-ready Markdown notes."
    )
    parser.add_argument("epub", help="Path to the input ePUB file")
    parser.add_argument("outfile", help="Path for the intermediate Markdown output")
    parser.add_argument("--attachments", default="attachments",
                        help="Directory for attachments (default: attachments)")
    parser.add_argument("--metadata", default="templates/metadata.yml",
                        help="Path to YAML metadata template (default: templates/metadata.yml)")
    parser.add_argument("--resources", default="templates/resources.md",
                        help="Path to resources Markdown template (default: templates/resources.md)")
    parser.add_argument("--outdir", default="notes",
                        help="Output directory for notes (default: notes)")
    parser.add_argument("--heading-level", default="1",
                        help="Heading level to split on (default: 1)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--step-1", action="store_true",
                       help="Perform only Step 1 and then exit")
    group.add_argument("--no-step-1", action="store_true",
                       help="Skip Step 1 and run from Step 2 onward")
    args = parser.parse_args()

    print("=== Starting ePUB to Obsidian Markdown Conversion Pipeline ===\n")
    if args.step_1:
        step_1(args.epub, args.attachments, args.outfile)
        print("Only Step 1 executed, exiting pipeline.")
        return
    if not args.no_step_1:
        step_1(args.epub, args.attachments, args.outfile)
    note_files = step_2(args.outfile, args.outdir, args.heading_level)
    if not note_files:
        print("No notes were created. Exiting pipeline early.")
        return
    step_3(note_files, args.metadata)
    step_4(note_files, args.resources)
    print("\n=== Pipeline Execution Complete ===")


if __name__ == '__main__':
    main()
