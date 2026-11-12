
import os
import zipfile


def is_course(folder):
    """Course must contain lessons/ and course_infos/."""
    return (
        os.path.isdir(os.path.join(folder, "lessons"))
        and os.path.isdir(os.path.join(folder, "course_infos"))
    )


def zip_course(course_folder, zip_path):
    """ZIP the entire course, preserving its folder name."""
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6
    ) as zf:
        for root, dirs, files in os.walk(course_folder):
            for file in files:
                file_path = os.path.join(root, file)

                arcname = os.path.relpath(
                    file_path,
                    os.path.dirname(course_folder)
                )

                zf.write(file_path, arcname)


def main():
    working_folder = input(
        "Enter working folder path: "
    ).strip().strip('"')

    working_folder = os.path.abspath(working_folder)

    if not os.path.isdir(working_folder):
        print("Error: Working folder does not exist.")
        return

    # Output is always a sibling of the input folder
    parent_folder = os.path.dirname(working_folder)

    output_folder = os.path.join(
        parent_folder,
        "System_course_zip"
    )

    os.makedirs(output_folder, exist_ok=True)

    total = 0

    for root, dirs, files in os.walk(working_folder):
        if not is_course(root):
            continue

        relative_path = os.path.relpath(
            root, working_folder
        )

        relative_parent = os.path.dirname(relative_path)

        output_dir = os.path.join(
            output_folder,
            relative_parent
        )

        os.makedirs(output_dir, exist_ok=True)

        course_name = os.path.basename(root)
        zip_path = os.path.join(
            output_dir,
            course_name + ".zip"
        )

        print(f"Zipping: {relative_path}")

        zip_course(root, zip_path)

        print(f"  Created: {zip_path}")
        total += 1

        # Do not search inside an identified course
        dirs.clear()

    print(f"\nCompleted! {total} courses zipped.")
    print(f"Output folder: {output_folder}")


if __name__ == "__main__":
    main()
