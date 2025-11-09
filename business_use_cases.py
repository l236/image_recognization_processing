#!/usr/bin/env python3
"""
Business Use Cases Demo
Demonstrates how the document parser can be used for:
1. Invoice Reimbursement (发票报销)
2. Contract Auditing (合同审核)
"""

from doc_parser import DocumentParserClient
import json
import os
from pathlib import Path

def load_business_config(scenario):
    """Load configuration for specific business scenario"""
    base_config = {
        "document_type": scenario,
        "ocr": {
            "engine": "pytesseract",
            "lang": "chi_sim+eng",
            "page_segmentation_mode": 6,
            "custom_words": [
                "发票", "合同", "金额", "日期", "编号", "公司",
                "报销", "审核", "审批", "reimbursement", "audit", "approval"
            ]
        },
        "extraction": {
            "fields": []
        },
        "validation": {
            "confidence_threshold": 0.7,
            "business_rules": {}
        }
    }

    if scenario == "invoice_reimbursement":
        base_config["extraction"]["fields"] = [
            {
                "name": "Document Type",
                "pattern": ["发票", "报销单", "invoice", "reimbursement"],
                "regex_patterns": ["(发票|报销单|invoice|reimbursement)"]
            },
            {
                "name": "Vendor/Company",
                "pattern": ["供应商", "公司", "vendor", "company"],
                "regex_patterns": [
                    "供应商[:：]\\s*([\\w\\s\u4e00-\u9fff]+)",
                    "公司[:：]\\s*([\\w\\s\u4e00-\u9fff]+)",
                    "([\\w\\s]+)(?:公司|Inc|Corp)"
                ]
            },
            {
                "name": "Invoice Amount",
                "pattern": ["金额", "总计", "amount", "total"],
                "regex_patterns": [
                    "金额[:：]\\s*[￥$]?([\\d,\\.]+)",
                    "总计[:：]\\s*[￥$]?([\\d,\\.]+)",
                    "￥([\\d,\\.]+)",
                    "\\$([\\d,\\.]+)"
                ],
                "post_process": "amount_normalize"
            },
            {
                "name": "Tax Amount",
                "pattern": ["税额", "税金", "tax", "vat"],
                "regex_patterns": [
                    "税额[:：]\\s*[￥$]?([\\d,\\.]+)",
                    "税金[:：]\\s*[￥$]?([\\d,\\.]+)"
                ],
                "post_process": "amount_normalize"
            },
            {
                "name": "Invoice Date",
                "pattern": ["日期", "开票日期", "date"],
                "entity_type": "DATE",
                "regex_patterns": [
                    "开票日期[:：]\\s*([\\d\\-\\./年月日\\s]+)",
                    "\\d{4}年\\d{1,2}月\\d{1,2}日",
                    "\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}"
                ],
                "post_process": "date_normalize"
            },
            {
                "name": "Invoice Number",
                "pattern": ["发票号码", "编号", "invoice number"],
                "regex_patterns": ["发票号码[:：]\\s*([\\w\\d\\-]+)"]
            }
        ]
        base_config["validation"]["business_rules"] = {
            "invoice_reimbursement": {
                "required_fields": ["Document Type", "Vendor/Company", "Invoice Amount", "Invoice Date"],
                "amount_limits": {"max_amount": 50000, "currency": "CNY"},
                "validation_checks": ["amount_reasonable", "date_not_future", "vendor_approved"]
            }
        }

    elif scenario == "contract_audit":
        base_config["extraction"]["fields"] = [
            {
                "name": "Document Type",
                "pattern": ["合同", "协议", "contract", "agreement"],
                "regex_patterns": ["(合同|协议|contract|agreement)"]
            },
            {
                "name": "Party A",
                "pattern": ["甲方", "party a", "employer"],
                "regex_patterns": [
                    "甲方[:：]\\s*([\\w\\s\u4e00-\u9fff]+)",
                    "Party A[:：]\\s*([\\w\\s\u4e00-\u9fff]+)"
                ]
            },
            {
                "name": "Party B",
                "pattern": ["乙方", "party b", "employee"],
                "regex_patterns": [
                    "乙方[:：]\\s*([\\w\\s\u4e00-\u9fff]+)",
                    "Party B[:：]\\s*([\\w\\s\u4e00-\u9fff]+)"
                ]
            },
            {
                "name": "Contract Amount",
                "pattern": ["金额", "报酬", "amount", "salary"],
                "regex_patterns": [
                    "金额[:：]\\s*[￥$]?([\\d,\\.]+)",
                    "报酬[:：]\\s*[￥$]?([\\d,\\.]+)",
                    "￥([\\d,\\.]+)",
                    "\\$([\\d,\\.]+)"
                ],
                "post_process": "amount_normalize"
            },
            {
                "name": "Contract Date",
                "pattern": ["签订日期", "日期", "contract date"],
                "entity_type": "DATE",
                "regex_patterns": [
                    "签订日期[:：]\\s*([\\d\\-\\./年月日\\s]+)",
                    "\\d{4}年\\d{1,2}月\\d{1,2}日"
                ],
                "post_process": "date_normalize"
            },
            {
                "name": "Contract Number",
                "pattern": ["合同编号", "contract number"],
                "regex_patterns": ["合同编号[:：]\\s*([\\w\\d\\-]+)"]
            },
            {
                "name": "Approval Status",
                "pattern": ["审批", "审核", "approval", "audit"],
                "regex_patterns": [
                    "审批[:：]\\s*([\\w\\s\u4e00-\u9fff]+)",
                    "审核[:：]\\s*([\\w\\s\u4e00-\u9fff]+)"
                ]
            }
        ]
        base_config["validation"]["business_rules"] = {
            "contract_audit": {
                "required_fields": ["Document Type", "Party A", "Party B", "Contract Amount", "Contract Date"],
                "validation_checks": ["amount_reasonable", "date_not_future", "parties_valid", "contract_format"]
            }
        }

    return base_config

def demo_invoice_reimbursement():
    """Demo invoice reimbursement workflow"""
    print("🧾 Invoice Reimbursement Demo")
    print("=" * 50)

    # Load invoice-specific configuration
    config = load_business_config("invoice_reimbursement")

    # Save config temporarily
    with open('temp_invoice_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # Initialize client with invoice config
    client = DocumentParserClient(config_path='temp_invoice_config.json')

    print("📋 Invoice Reimbursement Fields:")
    for field in config["extraction"]["fields"]:
        desc = field.get('description', 'Extract field value')
        print(f"  • {field['name']}: {desc}")

    print("\n✅ Business Rules:")
    rules = config["validation"]["business_rules"]["invoice_reimbursement"]
    print(f"  • Required Fields: {', '.join(rules['required_fields'])}")
    print(f"  • Max Amount: {rules['amount_limits']['max_amount']} {rules['amount_limits']['currency']}")
    print(f"  • Validation Checks: {', '.join(rules['validation_checks'])}")

    # Clean up
    os.remove('temp_invoice_config.json')

def demo_contract_audit():
    """Demo contract auditing workflow"""
    print("\n📄 Contract Audit Demo")
    print("=" * 50)

    # Load contract-specific configuration
    config = load_business_config("contract_audit")

    # Save config temporarily
    with open('temp_contract_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # Initialize client with contract config
    client = DocumentParserClient(config_path='temp_contract_config.json')

    print("📋 Contract Audit Fields:")
    for field in config["extraction"]["fields"]:
        desc = field.get('description', 'Extract field value')
        print(f"  • {field['name']}: {desc}")

    print("\n✅ Business Rules:")
    rules = config["validation"]["business_rules"]["contract_audit"]
    print(f"  • Required Fields: {', '.join(rules['required_fields'])}")
    print(f"  • Validation Checks: {', '.join(rules['validation_checks'])}")

    # Clean up
    os.remove('temp_contract_config.json')

def show_flexibility_demo():
    """Show how flexible the JSON configuration is"""
    print("\n🔧 Configuration Flexibility Demo")
    print("=" * 50)

    print("📝 The JSON configuration allows you to:")
    print("  • Add/remove fields based on business needs")
    print("  • Customize regex patterns for different document types")
    print("  • Set business-specific validation rules")
    print("  • Configure OCR settings per use case")
    print("  • Define amount limits and approval workflows")

    print("\n💼 Business Scenario Examples:")
    print("  • Invoice Reimbursement: Amount limits, tax validation, vendor approval")
    print("  • Contract Audit: Party validation, amount reasonableness, date checks")
    print("  • Purchase Orders: Item validation, budget checks, approval routing")
    print("  • Expense Reports: Category validation, policy compliance")

    print("\n🚀 Easy Integration:")
    print("  • Load different configs for different document types")
    print("  • API endpoints can accept scenario-specific configurations")
    print("  • Batch processing with scenario-based validation")
    print("  • Real-time validation feedback")

def main():
    """Main demo function"""
    print("🏢 Business Use Cases for Document Parser")
    print("Supporting Invoice Reimbursement (发票报销) and Contract Audit (合同审核)")
    print("=" * 80)

    demo_invoice_reimbursement()
    demo_contract_audit()
    show_flexibility_demo()

    print("\n" + "=" * 80)
    print("✅ Summary:")
    print("• JSON configuration is highly flexible for business scenarios")
    print("• Extracted fields can be customized per use case")
    print("• Business rules enable automated validation and compliance")
    print("• Supports both Chinese and English document processing")
    print("• Easy to extend for new business requirements")

if __name__ == "__main__":
    main()
