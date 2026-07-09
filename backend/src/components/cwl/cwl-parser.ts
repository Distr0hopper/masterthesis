import { ParameterDirection } from "../enums";
import * as yaml from 'js-yaml';
import {ParameterDto} from "../dto/parameter.dto";

export class CwlParser {
    static generateInputsYaml(parameters: Partial<ParameterDto>[], name: string, version: number): string {
        const inputs: Record<string, any> = {};
        for (const p of parameters) {
            if (!p.name) continue;
            const type = (p.cwlType ?? 'string').toLowerCase();
            inputs[p.name] = p.defaultValue !== null && p.defaultValue !== undefined
                ? this.coerceDefault(type, p.defaultValue)
                : this.placeholderForType(type);
        }
        const header = `# CWL inputs for ${name} v${version}\n# Usage: cwltool ${name}-v${version}.cwl inputs.yaml\n`;
        return header + yaml.dump(inputs, { lineWidth: -1, noRefs: true });
    }

    private static coerceDefault(type: string, value: string): any {
        if (type === 'double' || type === 'float') return parseFloat(value);
        if (type === 'int' || type === 'long') return parseInt(value, 10);
        if (type === 'boolean') return value === 'true';
        return value;
    }

    private static placeholderForType(type: string): any {
        if (type === 'file') return { class: 'File', path: '/path/to/input' };
        if (type === 'directory') return { class: 'Directory', location: '/path/to/dir' };
        if (type === 'double' || type === 'float') return 0.0;
        if (type === 'int' || type === 'long') return 0;
        if (type === 'boolean') return false;
        return '';
    }

    static injectDescription(cwlContent: string, description: string | null): string {
        const doc: any = yaml.load(cwlContent);
        if (description) {
            doc.doc = description;
        } else {
            delete doc.doc;
        }
        return yaml.dump(doc, { lineWidth: -1, noRefs: true });
    }

    static extractDescription(cwlContent: string): string | null {
        try {
            const doc: any = yaml.load(cwlContent);
            return doc?.doc ?? null;
        } catch {
            return null;
        }
    }

    static extractParameters(cwlContent: string): Partial<ParameterDto>[] {
        let doc: any;
        try {
            doc = yaml.load(cwlContent);
        } catch (err: any) {
            throw new Error(`YAML parse error: ${err.message}`);
        }

        const inputs: Record<string, any> = doc?.inputs ?? {};

        return Object.entries(inputs)
            .filter(([name]) => name !== 'input_rds')
            .map(([name, def]) => ({
                name,
                cwlType: String(def?.type ?? 'string').replace(/\?$/, ''),
                defaultValue: def?.default !== undefined ? String(def.default) : null,
                description: def?.doc ?? null,
                direction: ParameterDirection.INPUT,
            }));
    }
}