import { Parameter } from "../entities/parameter.entity";
import { ParameterDirection } from "../enums";
import * as yaml from 'js-yaml';

export class CwlParser {
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

    static extractParameters(cwlContent: string): Partial<Parameter>[] {
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