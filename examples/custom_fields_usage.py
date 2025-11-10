#!/usr/bin/env python3
"""
Custom Fields Usage Example
Demonstrates how users can define their own extraction fields
"""

from doc_parser import DocumentParserClient
import json

def demo_custom_fields():
    """Demo using custom-defined fields for medical documents"""
    print("🏥 Custom Fields Demo - Medical Document Processing")
    print("=" * 60)

    # Load custom configuration for medical documents
    with open('examples/custom_fields_config.json', 'r', encoding='utf-8') as f:
        custom_config = json.load(f)

    # Initialize client with custom config
    client = DocumentParserClient(config_dict=custom_config)

    print("📋 Custom Fields Defined:")
    for field in custom_config["extraction"]["fields"]:
        print(f"  • {field['name']}: {field['description']}")

    print("\n✅ Required Fields:")
    print(f"  • {', '.join(custom_config['validation']['required_fields'])}")

    print("\n🔧 Adaptive Fields:")
    print(f"  • Enabled: {custom_config['extraction']['enable_adaptive_fields']}")

    # Example: Process a medical document (simulated)
    print("\n📄 Processing Example Medical Document:")
    print("   (This would extract patient info, diagnosis, prescriptions, etc.)")

    # Show how to add more custom fields
    print("\n➕ How to Add More Custom Fields:")
    print("""
    Add to your config.json:

    {
      "name": "Your Custom Field",
      "pattern": ["keyword1", "keyword2"],
      "description": "What this field extracts",
      "regex_patterns": [
        "pattern1[:：]\\s*(.+)",
        "pattern2[:：]\\s*(.+)"
      ],
      "entity_type": "PERSON|ORG|DATE|MONEY",  // Optional NLP
      "post_process": "amount_normalize|date_normalize"  // Optional
    }
    """)

def show_field_types():
    """Show different types of fields users can define"""
    print("\n🎯 Field Definition Options:")
    print("=" * 40)

    examples = [
        {
            "type": "Pattern Matching",
            "example": {
                "name": "Department",
                "pattern": ["部门", "科室", "department"],
                "description": "Organizational department"
            }
        },
        {
            "type": "Regex Extraction",
            "example": {
                "name": "Phone Number",
                "regex_patterns": ["电话[:：]\\s*([\\d\\-\\s]+)"],
                "description": "Contact phone number"
            }
        },
        {
            "type": "NLP Entity Recognition",
            "example": {
                "name": "Person",
                "entity_type": "PERSON",
                "description": "Named person"
            }
        },
        {
            "type": "Post-processed",
            "example": {
                "name": "Budget Amount",
                "pattern": ["预算", "budget"],
                "post_process": "amount_normalize",
                "description": "Normalized monetary amount"
            }
        }
    ]

    for ex in examples:
        print(f"\n{ex['type']}:")
        print(f"  {json.dumps(ex['example'], ensure_ascii=False, indent=2)}")

def main():
    """Main demo function"""
    demo_custom_fields()
    show_field_types()

    print("\n" + "=" * 60)
    print("✅ Summary:")
    print("• Users can define unlimited custom fields")
    print("• Mix of user-defined + adaptive fields")
    print("• Flexible pattern matching and regex")
    print("• NLP entity recognition support")
    print("• Post-processing for data normalization")
    print("• Easy configuration via JSON")

if __name__ == "__main__":
    main()
