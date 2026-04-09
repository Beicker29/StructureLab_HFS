from collections import Counter

from src.steel_design.sections.loader import load_sections_from_excel


def main() -> None:
    sections = load_sections_from_excel("data/sections.xlsx")
    print(f"Loaded sections: {len(sections)}")
    type_counter = Counter(section.type for section in sections)
    for profile_type, count in sorted(type_counter.items()):
        print(f"{profile_type}: {count}")
    print("First five sections:")
    for section in sections[:5]:
        print(section.name, section.type)


if __name__ == "__main__":
    main()
