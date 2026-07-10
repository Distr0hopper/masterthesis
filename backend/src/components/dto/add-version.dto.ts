import { ApiProperty } from '@nestjs/swagger';
import { IsOptional, IsString } from 'class-validator';

export class AddVersionDto {
  @ApiProperty({ required: false, example: 'abc1234' })
  @IsOptional()
  @IsString()
  repoCommitSha?: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsString()
  description?: string;
}