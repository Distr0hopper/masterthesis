import { ApiProperty } from "@nestjs/swagger";
import { ComponentDomain, ComponentSource, VALID_DOMAINS } from "../enums";
import { ParameterDto } from "./parameter.dto";

export class ComponentDetailDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    name: string;

    @ApiProperty({ nullable: true })
    author: string | null;

    @ApiProperty({ nullable: true })
    description: string | null;

    @ApiProperty({ nullable: true })
    repoUrl: string | null;

    @ApiProperty({ nullable: true })
    repoCommitSha: string | null;

    @ApiProperty({ nullable: true })
    doi: string | null;

    @ApiProperty()
    version: number;

    @ApiProperty()
    cwlContent: string;

    @ApiProperty({ enum: VALID_DOMAINS })
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource })
    source: ComponentSource;

    @ApiProperty({ type: () => [ParameterDto] })
    parameters: ParameterDto[];

    @ApiProperty()
    createdAt: Date;
}